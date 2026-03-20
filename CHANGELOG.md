# CHANGELOG

すべての重要な変更点をここに記録します。  
フォーマットは Keep a Changelog に準拠します。

全般注意:
- このリポジトリは日本株自動売買システム「KabuSys」の初期実装です。
- 実装内容はコードベースから推測して記載しています（実行結果や外部環境は含みません）。

## [0.1.0] - 2026-03-20

### Added
- 基本パッケージ構成を追加
  - パッケージ識別子: `kabusys`、バージョン `0.1.0`（src/kabusys/__init__.py）。
  - サブパッケージ公開: data, strategy, execution, monitoring を __all__ に登録。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を上位ディレクトリから探索して自動検出（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト向け）。
  - .env パーサーの強化:
    - コメント行、`export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォートの有無による差別）。
  - Settings クラスを提供（properties 経由で必須値取得）。
    - J-Quants / kabu / Slack / DB パス等のプロパティを定義。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値集合を定義）。
    - パスは Path に変換して expanduser を実施。

- データ層（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制御: 固定間隔スロットリングで 120 req/min を守る RateLimiter 実装。
    - リトライ: 指数バックオフ（最大 3 回）、408/429/5xx を対象にリトライ。429 の場合は Retry-After ヘッダを考慮。
    - トークン管理: リフレッシュトークンから ID トークンを取得する get_id_token、モジュールレベルキャッシュと 401 発生時の自動リフレッシュ（1 回）を実装。
    - ページネーション対応の取得関数を実装:
      - fetch_daily_quotes（株価日足、ページネーション処理）
      - fetch_financial_statements（財務）
      - fetch_market_calendar（マーケットカレンダー）
    - DuckDB 保存ユーティリティ（冪等性確保）:
      - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT DO UPDATE による upsert 実装。
      - PK 欠損行はスキップし、スキップ数はログ出力。
    - 型変換ユーティリティ: _to_float, _to_int（安全な変換と None ルール）。
    - UTC の fetched_at を付与して Look-ahead トレースを容易に。

  - ニュース収集（src/kabusys/data/news_collector.py）
    - RSS フィードからの記事収集を想定したモジュール。
    - セキュリティ設計:
      - defusedxml を用いて XML Bomb 等を防御。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設定してメモリ DoS を軽減。
      - URL 正規化: トラッキングパラメータ（utm_ 等）を除去しクエリソート・フラグメント削除。
      - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保（コメント記載）。
      - HTTP/HTTPS スキーム制限、SSRF 対策（コメントおよび設計方針）。
    - バルク INSERT のチャンクサイズ制御（_INSERT_CHUNK_SIZE）やトランザクション単位での保存を想定。
    - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを設定。

- リサーチ（src/kabusys/research）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum, Volatility, Value（per, roe）などの定量ファクターを DuckDB の prices_daily / raw_financials を使って算出する関数を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日移動平均乖離）。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20 日ウィンドウなど）。
      - calc_value: per（株価/EPS、EPS=0 は None）, roe。raw_financials から最新報告を取得。
    - データ不足時の None 処理やスキャン範囲バッファ（カレンダー日での余裕）を考慮。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 将来リターン（デフォルト [1,5,21]）を一クエリで取得、存在しない場合は None。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。サンプル数不足（<3）の場合は None。
    - rank: 同順位は平均ランクを採るランク付け実装（丸めで ties 検出の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - すべて外部ライブラリに依存せず標準ライブラリと duckdb のみで実装。

  - 公開 API 再エクスポート（src/kabusys/research/__init__.py）

- 戦略層（src/kabusys/strategy）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - 研究環境で算出した生ファクター（momentum/volatility/value）を統合して features テーブルに保存する build_features を実装。
    - ユニバースフィルタを実装: 最低株価 = 300 円、20日平均売買代金 >= 5e8 円。
    - 正規化: zscore_normalize を利用し、指定カラムを Z スコア化して ±3 でクリップ。
    - 日付単位での置換（DELETE + INSERT）をトランザクションで行い冪等性を確保。
    - 価格取得は target_date 以前の最新価格を使用して休場日欠損等に対応。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成する generate_signals を実装。
    - スコア計算:
      - コンポーネント: momentum/value/volatility/liquidity/news。それぞれ専用の計算ロジックを実装（例: PER からの value スコア、atr_pct の反転シグモイドで volatility）。
      - シグモイド変換、None は中立 0.5 で補完。
      - 重み: デフォルト重みを定義し（momentum 0.4 など）、ユーザ指定 weights を検証・補完・再スケール。
      - BUY 閾値: デフォルト 0.60（threshold）。
    - Bear レジーム検知: ai_scores の regime_score 平均が負でサンプル数 >= 3 の場合は Bear とみなして BUY を抑制。
    - エグジット判定（売りシグナル生成）:
      - 実装済の条件: ストップロス（終値/avg_price -1 < -8%）、final_score < threshold。
      - 保有ポジションの価格欠損時は SELL 判定スキップ（誤クローズ回避）。
      - SELL 優先ポリシー: SELL 対象は BUY から除外しランクを再付与。
    - signals テーブルへの日付単位置換をトランザクションで実施。ログ出力により処理状況を記録。

- DBA / トランザクション・ロギング
  - 主要な DB 書き込み処理（features/signal 等）で BEGIN/COMMIT/ROLLBACK を利用し、ROLLBACK 失敗時は警告ログ出力。

### Security
- news_collector で defusedxml を利用して XML の脆弱性に対処。
- J-Quants クライアントでトークン取り扱いと HTTP エラー・ネットワーク障害に対する堅牢なリトライ実装。
- .env 読み込みでは既存の OS 環境変数を保護するため protected set を導入（.env.local でも上書き制御）。

### Documentation / Comments
- 各モジュールに詳細な docstring と設計方針・処理フロー・注意点のコメントを追加（ルックアヘッドバイアス等の説明や未実装箇所の注記）。

### Known limitations / TODO
- execution パッケージは空（発注ロジック・kabuステーション連携は未実装）。
- signal_generator の一部エグジット条件は未実装（コメントにて未実装箇所を明記）:
  - トレーリングストップ（peak_price 必要）
  - 時間決済（保有 60 営業日超過判定）
- calc_value は PBR・配当利回りを未実装。
- news_collector の記事ID生成・DB保存の具体的処理は設計に記載されているが、実際の RSS 取得/挿入フローはコードスニペット上の実装詳細が限定的（将来的な拡張が想定される）。
- 一部メソッドは duckdb 接続に依存（テストではモックが必要）。

---

今後のリリースで想定される改善点（例）
- execution 層の実装（kabuステーション API 経由の発注処理、認証・リトライ・シミュレーションモード）。
- ニュースパイプラインの完成（URL 正規化後のハッシュ化保存、news_symbols との紐付け）。
- インジケーター追加やファクターチューニング、AI スコア連携の強化。
- ユニットテストと統合テストの追加（DuckDB ベースのテストデータセットを含む）。

--------------------------------------------------------------------
参考: Keep a Changelog - https://keepachangelog.com/en/1.0.0/