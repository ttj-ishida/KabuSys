# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。  
このファイルはコードベースから推測して自動生成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-03-20

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を導入 (src/kabusys/__init__.py): __version__ = "0.1.0"、公開モジュール一覧 (__all__) を定義。
- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能:
    - プロジェクトルート検出: .git または pyproject.toml を探索してプロジェクトルートを特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途）。
  - .env パーサを実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理（クォート有無に応じた挙動）。
    - 無効行のスキップ、キー欠損時のスキップ。
  - _load_env_file による protected（既存 OS 環境変数）保護オプション、override フラグを実装。
  - Settings による各種プロパティを提供（J-Quants / kabu API / Slack / データベースパス / 環境種別やログレベルの検証など）。
- データ収集・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装:
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - リトライ（指数バックオフ、最大試行回数の制御）、HTTP 408/429/5xx に対するリトライ処理。
    - 401 応答時の自動トークンリフレッシュ（1 回のみ再取得して再試行）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）。
    - DuckDB への保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等性を確保。
    - レスポンスのページネーションキー重複検出でループ終了。
  - モジュールレベルの ID トークンキャッシュを実装し、ページネーション間でトークンを共有。
  - 型変換ユーティリティ (_to_float / _to_int) を実装（安全に None を返す挙動）。
- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集モジュールを実装（デフォルトの RSS ソースを一件含む）。
  - 記事前処理機能:
    - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント削除、クエリパラメータソート）。
    - 記事 ID を正規化 URL に基づく SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
  - 受信サイズ上限設定（MAX_RESPONSE_BYTES = 10MB）やバルク挿入チャンクサイズの導入でリソース保護・性能を考慮。
  - defusedxml を用いた RSS XML パース（XML Bomb 対策）。
- 研究用モジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio を計算（true range の NULL 伝播に注意）。
    - calc_value: raw_financials と prices_daily を組み合わせて per / roe を計算（最新の report_date を使用）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、外部依存なしで実行可能。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（単一クエリで取得）。
    - calc_ic: スピアマンのランク相関（IC）を計算。十分なサンプルがない場合は None を返す。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクで扱うランク関数（round による丸めで ties を安定検出）。
  - 研究 API を __init__ で再公開。
- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features を実装:
    - research の calc_momentum / calc_volatility / calc_value を組み合わせて生ファクターをマージ。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT をトランザクションで行い冪等性を保証）。
- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals を実装:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、None のコンポーネントは中立 0.5 で補完。
    - デフォルト重みと閾値を定義（デフォルト閾値 0.60）。
    - ユーザー指定 weights のバリデーションと合計が 1.0 でない場合の再スケール処理。
    - Bear レジーム検知（ai_scores の regime_score 平均が負でサンプル数閾値を超える場合）による BUY 抑制。
    - SELL シグナル判定（stop_loss: -8% を超える損失、final_score が閾値未満）を実装。ポジションが price 欠損の場合は判定をスキップ。
    - SELL 優先ポリシー: SELL 対象は BUY から除外しランクを再付与。
    - signals テーブルへ日付単位の置換（トランザクション + bulk insert で原子性を確保）。
- strategy パッケージの公開 API を __init__ で定義（build_features, generate_signals）。

### セキュリティ (Security)
- news_collector で defusedxml を使用して XML 攻撃を軽減。
- ニュース収集で受信サイズ上限を設け、メモリ DoS を低減。
- URL 正規化でスキーム検査（HTTP/HTTPS 想定）とトラッキングパラメータ除去を実装し、将来的な SSRF/追跡リスクの低減に備える。
- jquants_client の HTTP/ネットワークエラー処理でリトライやタイムアウトを考慮し、失敗時の情報露出を最小化。

### 注意点 / 実装上の設計方針
- 多くの処理は DuckDB 接続を受け取り prices_daily/raw_*/features/ai_scores/positions などのテーブルを参照する設計になっている。事前に期待されるスキーマを作成しておく必要がある。
- ルックアヘッドバイアス対策のため、すべての集計・シグナル生成処理は target_date 時点のデータのみを参照する方針で実装。
- データ保存関数は冪等性（ON CONFLICT DO UPDATE / INSERT ... DO NOTHING 等）やトランザクションでの原子性を重視している。
- 一部の機能（例: signal_generator のトレーリングストップや時間決済）は positions テーブルに追加情報（peak_price / entry_date 等）が必要で現時点では未実装としている旨の注記がある。

### 既知の未実装 / 将来的な拡張候補
- signal_generator におけるトレーリングストップや時間決済の条件は未実装（positions に peak_price/entry_date が必要）。
- news_collector における取得時の gzip/圧縮対応や詳細な HTTP ヘッダ制御については将来的に拡張可能（実装の痕跡はあるが完全実装はソース確認が必要）。
- monitoring / execution 層の詳細な実装は本差分に含まれていない（パッケージ公開名に含まれるが個別実装は未提供）。

---

本 CHANGELOG はソースコードからの推測に基づくものであり、実際の変更履歴・プロジェクト管理上のリリースノートとは差異がある可能性があります。必要であれば、さらに細かいファイル単位の変更点やサンプル出力（関数の入出力仕様）を追記します。