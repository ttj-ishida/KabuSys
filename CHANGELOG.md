# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

- なし

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買 / データ基盤 / リサーチ用ユーティリティをまとめた最初の安定版リリースです。以下の主要機能を含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの基本構成とバージョン管理を追加（__version__ = 0.1.0）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定 (kabusys.config)
  - .env および .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート（テスト用途）。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 環境変数取得ラッパ Settings を実装（必須変数チェック _require、型変換、既定値、値制約の検証）。
  - 主要設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント集計: news_nlp.score_news を追加。
    - ニュース集約（前日 15:00 JST ～ 当日 08:30 JST のウィンドウ）→ 銘柄単位で記事を結合して OpenAI に送信 → ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大化対策（記事数上限・文字数トリム）。
    - JSON mode の応答パースと復元処理、レスポンスの厳格なバリデーション実装。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）と指数バックオフ、フェイルセーフでのスキップ挙動。
    - テスト容易性: _call_openai_api の差し替え可能性を意識した実装。
    - DuckDB executemany における空リスト回避（互換性対策）。

  - 市場レジーム判定: regime_detector.score_regime を追加。
    - ETF (1321) の 200 日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して日次レジーム判定（bull/neutral/bear）。
    - prices_daily / raw_news / market_regime テーブルを参照・更新。書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。
    - マクロニュース抽出キーワード群定義と OpenAI 呼び出し（gpt-4o-mini）、API 再試行ロジック、フェイルセーフ（API 失敗時は macro_sentiment = 0.0）。
    - ルックアヘッドバイアス回避の設計（target_date 未満のみを参照、datetime.today() を使用しない）。

- データ（Data Platform）モジュール (kabusys.data)
  - カレンダー管理: calendar_management を追加。
    - market_calendar を用いた営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先・未登録日は曜日ベースのフォールバック、最大探索日数制限による安全対策。
    - calendar_update_job: J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存のバッチジョブ実装。
  - ETL 基盤: pipeline.ETLResult と data.etl の公開。
    - 差分更新、バックフィル、品質チェック（quality モジュールと連携）を想定した ETLResult 構造体を導入。
    - DuckDB の日付最大値取得、テーブル存在チェック等のユーティリティを実装。
  - jquants_client を利用したデータ保存インターフェースとの連携点（fetch/save を呼び出す想定。実装は別モジュール）。

- リサーチ（kabusys.research）
  - factor_research: ファクター計算機能を追加。
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時の None ハンドリング）。
    - ボラティリティ・流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - バリュー: PER、ROE（raw_financials から過去最新の財務データを結合）。
    - DuckDB SQL + Python による実装・ログ出力。
  - feature_exploration: 特徴量探索ユーティリティを追加。
    - 将来リターン計算（calc_forward_returns、任意ホライズン、入力検証）。
    - IC（Information Coefficient、Spearman ρ）計算（calc_ic）。
    - ランク変換（rank）、ファクター統計サマリー（factor_summary）。
    - 外部ライブラリ非依存（標準ライブラリのみ）での実装。

### 変更 (Changed)
- DuckDB 互換性を考慮した実装上の配慮を反映
  - executemany に空リストを渡さない（DuckDB 0.10 の制約対応）。
  - 日付値の DuckDB→Python 変換ユーティリティ (_to_date) を提供。
- OpenAI 呼び出しは JSON mode を利用し、応答整形や例外処理を強化。
- datetime.today()/date.today() を直接参照しない設計に統一（ルックアヘッドバイアス防止）。

### 修正 (Fixed)
- DB トランザクション失敗時に ROLLBACK を試行しつつ失敗ログを出力して上位へ例外を伝播する安全なエラーハンドリングを実装（score_regime / score_news 他）。
- API レスポンスパース失敗時に例外を上げずフェイルセーフ（スコア 0.0・空スコア辞書）で継続するように安定化。

### 注意事項 / マイグレーション (Notes)
- 必須環境変数:
  - OpenAI API: OPENAI_API_KEY（news_nlp.score_news / regime_detector.score_regime は未指定時 ValueError を送出）。
  - J-Quants: JQUANTS_REFRESH_TOKEN
  - kabuステーション: KABU_API_PASSWORD
  - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトDBパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- .env 読み込み順序: OS 環境 > .env.local > .env。OS 環境を保護する保護セットを導入。
- テストのしやすさ:
  - OpenAI 呼び出し用の内部関数（各モジュール内の _call_openai_api）は unittest.mock.patch で差し替え可能。
- ルックアヘッドバイアスに注意:
  - すべての分析/スコアリング関数は target_date を明示的に取る設計（内部で現在日を参照しない）。

### 既知の制限 (Known limitations)
- PBR・配当利回りなどの一部バリューファクターは未実装。
- news_nlp/regime_detector は OpenAI の JSON mode と特定モデル（gpt-4o-mini）に依存する（将来の SDK 変更に注意）。
- jquants_client / quality モジュールの実装は別途必要（本リリースではインターフェース呼び出しを想定）。

### セキュリティ (Security)
- 特に無し。

---

配布・利用にあたって不明点や追加で記載してほしい項目があれば教えてください。