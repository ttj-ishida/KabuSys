# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠します。  
このリポジトリの初回公開バージョンをコードベースから推測して作成した CHANGELOG です。

- 変更履歴は意図的にコード実装の設計方針・挙動・公開 API を中心にまとめています。
- バージョン番号は package の __version__（0.1.0）に合わせています。

## [Unreleased]
- （現時点で未リリースの変更なし）

## [0.1.0] - 2026-04-01
初回リリース（コードベースから推測）

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージを追加。公開モジュール群: data, research, ai, （および strategy, execution, monitoring を __all__ として宣言）。
  - バージョン定義: __version__ = "0.1.0"。

- 環境設定 / config
  - Settings クラスを導入し、環境変数から構成を取得する統一インタフェースを提供（例: jquants_refresh_token, kabu_api_password, slack_bot_token, slack_channel_id）。
  - デフォルト値・型変換を備えたプロパティを実装（例: duckdb_path, sqlite_path, pid_file_path, cpu/memory/disk 閾値, env/log_level 判定）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（有効値セットを定義）。
  - .env 自動ロード機能を実装:
    - プロジェクトルート検出（.git または pyproject.toml をルートと判定）に基づき .env と .env.local を自動読み込み。
    - 読み込みの優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を実装。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントを考慮した堅牢な実装。

- AI（自然言語処理）機能
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）にバッチ送信して銘柄単位のセンチメントを算出。
    - チャンク処理（最大 20 銘柄／コール）・トリム（記事数／文字数の上限）・エクスポネンシャルバックオフによるリトライを実装。
    - レスポンス検証機構（JSON の抽出・バリデーション・スコアの数値化・±1.0 クリップ）を実装。
    - 成果を ai_scores テーブルへ冪等的に書き込む（DELETE→INSERT、部分失敗時に既存スコアを保護）。
    - calc_news_window ユーティリティを提供（対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC で扱う）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し、合成スコア生成、market_regime テーブルへの冪等書き込みを実装。
    - LLM 呼び出し失敗やパース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - OpenAI 呼び出しは専用ラッパー関数で実装し、テスト時にモックしやすい設計。

- Research（ファクター・特徴量）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200日 MA 乖離）を計算する calc_momentum を提供。
    - ボラティリティ / 流動性: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金、出来高比率を計算する calc_volatility を提供。
    - バリュー: raw_financials から最新の財務データを取得し PER / ROE を計算する calc_value を提供。
    - DuckDB ベースの SQL + Python 実装で、外部 API や発注系にはアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns（任意ホライズン: デフォルト [1,5,21]）。
    - IC（Spearman ランク相関）計算: calc_ic（factor と forward を code で結合して計算、3 銘柄未満は None）。
    - 統計サマリ: factor_summary（count/mean/std/min/max/median）。
    - ランキングユーティリティ: rank（同順位は平均ランク）。
    - 依存を標準ライブラリのみとする実装方針。

- Data（ETL / カレンダー）
  - カレンダー管理（kabusys.data.calendar_management）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day の営業日ロジックを提供。
    - market_calendar が未取得の場合は曜日ベース（週末除外）でフォールバックする振る舞いを実装。
    - calendar_update_job を提供し、J-Quants API 経由で市場カレンダーを差分取得して保存（バックフィル／健全性チェックあり）。
    - 最大探索範囲（_MAX_SEARCH_DAYS）やバックフィル日数など安全策を実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを実装して ETL の結果（取得件数・保存件数・品質問題・エラー）を集約。
    - 差分取得・保存・品質チェック（quality モジュール連携）を想定した設計。jquants_client を通じた保存処理に対応。
    - ETL の設計方針として「部分失敗を許容して進める（Fail-Fast ではない）」「id_token の注入でテスト容易化」を採用。
  - データ関連ユーティリティの公開（data.__init__、etl の再エクスポート等）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- ルックアヘッド・バイアス対策を各アルゴリズム設計に組み込み:
  - datetime.today()/date.today() に依存しない API（全て target_date ベースで計算）。
  - prices_daily クエリやウィンドウ計算で date < target_date / date BETWEEN を適切に使用。
- OpenAI / ネットワーク系のエラー耐性強化:
  - レート制限・接続断・タイムアウト・5xx に対するリトライ（指数バックオフ）を実装し、最終的にスコアを 0.0 へフォールバックする安全策を採用。
- .env 読み取りの堅牢化:
  - export プレフィックスに対応、引用符内のエスケープ処理、インラインコメント規則の実装で .env ファイルの互換性を向上。
- DuckDB 周りの互換性配慮:
  - executemany に空リストを渡さない等、DuckDB バージョン差異への防御を実装（部分置換ロジック等）。

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キーは必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出して明示的に失敗。
- .env 自動ロード時に既存の OS 環境変数を保護（上書き除外）する仕組みを導入。

### 既知の制約・注意点 (Notes / Known issues)
- OpenAI SDK の JSON mode（response_format={"type":"json_object"}）を利用しているため、SDK のバージョン差や今後の仕様変更に依存する可能性あり。テスト用に _call_openai_api をモック可能にしている。
- DuckDB の一部バージョンでのパラメタバインドの振る舞いに配慮した実装（executemany の扱いなど）をしているが、運用環境ではバージョン確認を推奨。
- ai_scores / market_regime / prices_daily などのテーブルスキーマが前提となる（テスト／運用環境でテーブルが存在することを想定）。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後や別配置環境では KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

---

今後のリリースでは、以下の点が想定されます（参考）
- strategy / execution / monitoring モジュールの具体的な実装公開（現時点では __all__ に名前のみ定義）。
- J-Quants クライアント周り（jquants_client）の具体的メソッド仕様と ETL の結合テスト強化。
- テスト用ユーティリティ（DuckDB テストフィクスチャ、OpenAI 呼び出しのスタブ等）の追加。

（以上）