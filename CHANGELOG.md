Keep a Changelog 準拠 — 日本語 CHANGELOG.md

注意: 以下は提供されたコードベースの内容から推測して作成した変更履歴です。
バージョン番号はパッケージ内の __version__ (0.1.0) を使用しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-19
-------------------
Added
- 基本パッケージ情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード実装
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサに対応:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い等を考慮
  - 上書きポリシー:
    - .env.local は .env より優先して上書き（ただし OS 環境変数は保護）
  - Settings クラスを提供しアプリケーション設定をプロパティ経由で取得
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等必須項目は未設定時に例外を発生
    - DB パス（duckdb/sqlite）や環境（development/paper_trading/live）・ログレベルの検証を含む

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装
    - 固定間隔のレートリミッタ（120 req/min）を搭載
    - 再試行（指数バックオフ、最大 3 回）とリトライ対象ステータス管理（408/429/5xx）
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有
    - ページネーション対応（pagination_key を利用）
    - JSON デコードエラーやネットワークエラーの適切なハンドリング
  - 認証補助関数: get_id_token（リフレッシュトークン -> idToken）
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB 保存関数（冪等保存を重視）
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE 実装、fetched_at を UTC で記録
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE 実装
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE 実装
  - 入出力ユーティリティ: 値を安全に float/int に変換する関数（_to_float, _to_int）
  - 実装上の配慮: PK 欠損行のスキップとログ出力、Retry-After ヘッダ優先のリトライ待機等

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事収集・正規化する機能を追加
    - デフォルト RSS ソースの定義（例: Yahoo Finance）
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント削除、クエリのソート）
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を保証
    - defusedxml を用いた安全な XML パース（XML Bomb 等対策）
    - HTTP(S) スキーム以外の URL 拒否、受信最大バイト数制限（デフォルト 10 MB）
    - テキスト前処理（URL 除去・空白正規化）
    - DB へのバルク INSERT（チャンクサイズ制御）とトランザクションまとめ保存、ON CONFLICT DO NOTHING 等で冪等性を確保
    - 実装によるメモリ/SSRF 対策や挿入件数の正確なカウント

- リサーチ機能 (src/kabusys/research/)
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、相対 ATR）、バリュー（PER, ROE）、流動性（20日平均売買代金、出来高比率）などのファクター計算関数を実装
    - DuckDB の SQL とウィンドウ関数を活用して効率的に算出
    - データ不足時の None ハンドリング
  - feature_exploration.py
    - calc_forward_returns（target_date から各ホライズンの将来リターンを計算）
    - calc_ic（Spearman ランク相関による IC 計算）
    - factor_summary（各カラムの count/mean/std/min/max/median を算出）
    - rank（同順位は平均ランクを付与するランク関数）
    - 標準ライブラリのみで実装（外部依存を最小化）
  - research パッケージの __all__ に主要関数を公開

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date) を実装
    - research の calc_momentum/calc_volatility/calc_value を利用して生ファクターを取得
    - 株価・流動性を用いたユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装
    - 指定カラムについて Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ
    - features テーブルへ日付単位で置換（BEGIN / DELETE / INSERT / COMMIT）して冪等性と原子性を確保
    - ログ出力（処理件数等）

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装
    - features と ai_scores を統合してファクターごとのコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
      - Z スコアをシグモイド変換して [0,1] にマップ
      - PER ベースのバリュースコア、ATR 反転のボラティリティスコア等を実装
    - 重みの検証と補完（デフォルト重みを用い、合計が 1 でない場合の再スケール）
    - Bear レジーム判定（ai_scores の regime_score の平均が負で、十分なサンプル数がある場合に BUY を抑制）
    - BUY シグナル: threshold を超えた銘柄をスコア降順で選出（Bear 時は抑制）
    - SELL シグナル（エグジット判定）:
      - ストップロス: 直近終値 / avg_price - 1 <= -8%
      - スコア低下: final_score が threshold 未満
      - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）
    - ログ出力（BUY/SELL 件数など）
  - 設計上の配慮:
    - ルックアヘッドバイアスの回避（target_date 時点のデータのみ参照）
    - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止

- パッケージのエクスポート
  - strategy パッケージで build_features / generate_signals を公開
  - research パッケージで主要ユーティリティを公開
  - top-level __all__ に data/strategy/execution/monitoring を記載（execution/monitoring はまだ中身が薄い可能性あり）

Fixed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Known limitations / TODO
- signal_generator の SELL 条件に記載されている未実装要素:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過等）
- execution / monitoring パッケージは __all__ に含まれるが、今回提供されたコードでは実装が薄い（将来的な機能追加予定）。
- news_collector の記事 → 銘柄マッチング（news_symbols への紐付け）は示唆されているが、完全なパイプラインの全詳細はコード断片からは未確定。
- research モジュールは外部ライブラリ非依存を意図しているが、大規模データ処理時の最適化（メモリ・速度）は将来的な改善余地あり。

開発者向けメモ
- DB スキーマ（tables: raw_prices, raw_financials, market_calendar, prices_daily, raw_financials, features, ai_scores, positions, signals 等）が前提になっており、実行前に DuckDB のスキーマ準備が必要
- 環境変数の必須項目が不足すると Settings プロパティで ValueError が発生するため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するか適切に環境を設定してください

以上。