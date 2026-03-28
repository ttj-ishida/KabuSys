# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
初期リリース (パッケージバージョンは src/kabusys/__init__.py の __version__ を参照)。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ初期公開
  - kabusys パッケージの基本構成を追加。エントリポイントであるバージョンは 0.1.0。
  - モジュール群を公開: data, research, ai, config, monitoring, strategy, execution（__all__ で公開済み）。

- 環境設定・ロード機能 (kabusys.config)
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサーを実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 環境変数要求用ヘルパー _require と Settings クラスを提供。各種設定プロパティを定義:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）, LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
  - Settings に is_live/is_paper/is_dev のユーティリティプロパティを追加。

- AI 関連 (kabusys.ai)
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でバッチ評価し、銘柄ごとのセンチメントスコア（ai_scores）を生成・DB 書き込みする機能を実装。
    - タイムウィンドウ計算 (JST基準 → UTCへ変換)。
    - 1 銘柄あたりの記事集約（最大記事数・文字数トリム）。
    - 最大 BATCH_SIZE（デフォルト 20）単位で API バッチ送信。
    - エラー時は再試行（429/ネットワーク/タイムアウト/5xx に対して指数バックオフ）、但し最終的に失敗しても例外を投げずフェイルセーフでスキップ。
    - JSON Mode 応答を検証・パース。スコアは ±1 にクリップ。
    - テスト用に OpenAI 呼び出しを差し替え可能（unittest.mock.patch 対応）。
  - regime_detector: ETF (1321) の 200 日移動平均乖離（重み 70%）とニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・market_regime テーブルに冪等書き込みする機能を実装。
    - ma200 の計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。
    - マクロニュース抽出（キーワードリスト） → OpenAI に送信して macro_sentiment を取得、失敗時は 0.0 をフォールバック。
    - スコア合成・閾値判定・トランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。
    - OpenAI 呼び出しに対するリトライ・バックオフ実装。

- データ基盤 (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理：market_calendar を元に営業日判定 / 前後営業日取得 / 期間内営業日取得 / SQ 日判定ロジックを実装。
    - DB にカレンダー情報が無い場合は曜日ベースのフォールバック（週末を非営業日）を使用。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得・保存（バックフィル・健全性チェックを含む）。
  - pipeline:
    - ETLResult データクラスを公開（ETL 実行結果・品質問題やエラーを保持）。
    - ETL 用ユーティリティ（最終日取得、テーブル存在チェック等）を実装。
    - デフォルトのバックフィルやカレンダー先読み設定など ETL ポリシーを定義（定数化）。
  - etl モジュールで ETLResult を re-export。

- 研究用ユーティリティ (kabusys.research)
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）の計算関数を実装。
    - DuckDB 上でウィンドウ関数等を利用して計算。データ不足時の None 取り扱いを明確化。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン）、IC（スピアマンランク相関）、rank（同順位は平均ランク）、factor_summary（統計サマリー）等を実装。
    - pandas 等外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

- 共通事項
  - DuckDB を主要なデータレイヤとして想定。多くの関数は DuckDB 接続を受け、prices_daily 等のテーブルへ SQL でアクセス。
  - OpenAI API を使用する処理は api_key を引数で注入でき、テスト時のキー依存を低減。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- API キー・シークレットは環境変数で管理（OpenAI: OPENAI_API_KEY、J-Quants: JQUANTS_REFRESH_TOKEN、kabu: KABU_API_PASSWORD、Slack: SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）。
- .env 自動読み込みはプロジェクトルート検出に基づく。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- .env 読み込みで OS 環境変数（プロセス環境）を保護する protected キー機構を採用。

### 既知の注意点 / マイグレーション情報 (Notes)
- OpenAI 連携:
  - API レスポンスは JSON モードを想定しているが、前後に余計なテキストが混ざるケースへも耐性を持たせるパース処理を実装している。
  - API 呼び出し失敗時は最終的にスコアを 0.0 にフォールバックする等、フェイルセーフが優先されるため、部分的な評価失敗はシステム全体の停止を招きにくい設計。
  - テストでは kabusys.ai.* の _call_openai_api をモックして API 呼び出しを置き換え可能。
- 日付・時間の扱い:
  - ルックアヘッドバイアス防止のため、本実装は内部で datetime.today() / date.today() を利用しないよう配慮。target_date を明示して処理を行う設計。
  - ニュースウィンドウ計算等は JST 表現から UTC naive datetime に変換して DB (UTC 保存想定) と照合する実装になっている。
- DuckDB executemany の制約対応:
  - DuckDB（特に 0.10 系）では executemany に空リストを渡せない点に対応したガードを設置。
- カレンダー:
  - market_calendar が部分的にしか登録されていない場合でも next_trading_day / prev_trading_day / get_trading_days の挙動が一貫するように DB 優先 → 未登録は曜日フォールバックの方針を採用。
- 設定検証:
  - KABUSYS_ENV と LOG_LEVEL は許可値の検証を行い、不正値の場合は ValueError を投げる。

### 互換性 (Compatibility)
- 初回公開のため過去バージョン互換性に関する破壊的変更は無し。

---

今後のリリースでは、モニタリング周りの実装（monitoring モジュール）、発注／実行（execution）やストラテジー（strategy）の具体的な実装拡張、テストカバレッジ向上、外部 API（J-Quants / kabuステーション）クライアントの堅牢化・リトライ戦略の改善などを予定しています。必要に応じて CHANGELOG を更新します。