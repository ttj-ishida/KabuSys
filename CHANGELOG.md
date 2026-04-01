# Changelog

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。日付は本リリースの想定日です。

## [0.1.0] - 2026-04-01

### 追加 (Added)
- 初版リリース。モジュール構成の追加と主要機能を実装。
- パッケージ初期化
  - kabusys パッケージのエントリポイントを定義（__version__ = 0.1.0、公開サブパッケージ指定）。
- 環境設定/ロード（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルートを `.git` または `pyproject.toml` を基準に探索する実装（カレントワークディレクトリに依存しない）。
  - .env と .env.local の読み込み優先順位（OS 環境変数 > .env.local > .env）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - シェル形式の `export KEY=val`、クォート内のバックスラッシュエスケープ、行末コメントの扱い等に対応する .env パーサーを提供。
  - 必須環境変数検査用のヘルパー（_require）および Settings クラスを実装。公開プロパティ:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`, `sqlite_path`
    - 監視設定: `pid_file_path`, `cpu_threshold_pct`, `memory_threshold_pct`, `disk_threshold_pct`
    - 実行環境判定: `env`, `log_level`, `is_live`, `is_paper`, `is_dev`
  - 設定値に対するバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値検査）。
- AI サブパッケージ（kabusys.ai）
  - news_nlp: ニュース記事を OpenAI (gpt-4o-mini, JSON Mode) に投げて銘柄別センチメントを算出し `ai_scores` テーブルへ書き込む機能（score_news）。
    - JST 時間ウィンドウの計算ユーティリティ（calc_news_window）。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたり記事数・文字数トリム、応答バリデーション、±1.0 クリッピング、失敗時フェイルセーフ（スキップ）。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフ実装。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（unittest.mock.patch 対応）。
    - DuckDB の executemany の仕様差への対処（空リスト渡し回避）。
  - regime_detector: ETF 1321（ニッケイETF）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出する機能（score_regime）。
    - ma200_ratio の計算、マクロキーワードに基づくニュース抽出、OpenAI 呼び出し（JSON Mode）での macro_sentiment 評価、スコア合成、`market_regime` テーブルへの冪等書き込みを実装。
    - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - OpenAI クライアントは引数 api_key で注入可能（環境変数 OPENAI_API_KEY も参照）。
- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー（market_calendar）の管理と営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未登録の場合は曜日ベース（平日が営業日）でフォールバック。
    - calendar_update_job: J-Quants API からの差分取得・バックフィル（直近数日）・健全性チェックを行い `market_calendar` を冪等更新するバッチ処理を実装。
  - pipeline / ETL（kabusys.data.pipeline）
    - ETLResult データクラスを追加（ETL の取得/保存数、品質問題、エラー等を格納）。
    - 差分更新・バックフィル・品質チェック（quality モジュール）を行う設計を反映したユーティリティを実装（実装の詳細・呼び出しインターフェースを想定）。
  - etl.py: pipeline.ETLResult の再エクスポート。
- 研究用ユーティリティ（kabusys.research）
  - factor_research: モメンタム/バリュー/ボラティリティ等、StrategyModel に基づいたファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離など（データ不足時の None 処理）。
    - calc_volatility: 20 日 ATR（true range の NULL 伝播を明示的に扱う）、平均売買代金、出来高比率等。
    - calc_value: raw_financials と prices_daily を組み合わせた PER, ROE の計算（最新財務レコードの取得）。
  - feature_exploration: 将来リターン算出と統計解析機能を実装。
    - calc_forward_returns: 任意ホライズンの将来リターンを一度の SQL で取得。
    - calc_ic: スピアマンランク相関（IC）計算（最少有効レコード数チェック）。
    - rank: タイ（同順位）に平均ランクを割り当てるランク化実装（丸め対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出する統計サマリ機能。
- 内部実装上の設計・安全対策
  - ルックアヘッドバイアス防止: 全ての分析処理（news/regs/factors 等）は内部で datetime.today()/date.today() を直接参照しない設計（target_date 引数ベース）。
  - DB 書き込みは冪等性を重視（BEGIN / DELETE / INSERT / COMMIT、ON CONFLICT 想定）。
  - OpenAI との対話は JSON Mode を利用しレスポンスを厳密にパースする設計。
  - API 呼び出し時のリトライ戦略（429, network, timeout, 5xx）と、非リトライ対象のエラー区別を実装。
  - テスト容易性のため、OpenAI 呼び出し関数をモジュール単位で差し替え可能にしている（patch 対応）。

### 変更 (Changed)
- （初版リリースのため該当なし）

### 修正 (Fixed)
- （初版リリースのため該当なし）

### 廃止 (Deprecated)
- （初版リリースのため該当なし）

### 削除 (Removed)
- （初版リリースのため該当なし）

### セキュリティ (Security)
- 環境変数で扱う機密情報（OpenAI API キー、J-Quants トークン、kabu API パスワード、Slack トークン等）は Settings 経由で取り扱うことを想定。自動 .env ロードはプロジェクトルート検出の成功時のみ実行され、必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- .env 読み込み時に既存の OS 環境変数を保護する仕組み（protected set）を導入。

---

補足 / マイグレーションノート
- OpenAI を利用する機能（score_news, score_regime）は事前に `OPENAI_API_KEY` を環境変数で設定するか、各関数に `api_key` を渡す必要があります。キー未設定時は ValueError を送出します。
- DuckDB の executemany に空リストを渡せないバージョンへの対応（空チェックを行ってから executemany）を行っているため、DB バージョンによる互換性は考慮済みです。
- ETL / カレンダー更新 / AI スコアリングはいずれも部分失敗時に既存データを不必要に削除しない（code を絞って DELETE → INSERT）設計になっています。
- テスト時は OpenAI 呼び出しポイント（各モジュールの _call_openai_api）をパッチして疑似レスポンスを注入することができます。

既知の制約
- 一部の外部クライアント（J-Quants, OpenAI）の具体的実装は依存モジュールに委譲されており、実稼働にはそれらクライアントの設定が必要です（jquants_client 等）。
- calendar_update_job 等は実際の API レスポンスに依存するため、稼働環境での API エラーに対してはログ出力・スキップするフェイルセーフ挙動を取ります。

-----