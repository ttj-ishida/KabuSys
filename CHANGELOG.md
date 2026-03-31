# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトではセマンティックバージョニングを採用します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31
初回リリース。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を公開（src/kabusys/__init__.py）。
  - サブパッケージ（data, research, ai, monitoring, execution, strategy 等）の公開を想定したモジュール構成。

- 環境設定 / 設定読み込み（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込みを自動化（プロジェクトルート検出: .git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装: export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、行内コメント（条件付き）に対応。
  - Settings クラスを提供し、以下の主要設定をプロパティ経由で取得可能（必須項目は未設定時に ValueError を送出）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（API 呼び出し時に参照）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（デフォルト: data/monitoring.db）
    - PID_FILE_PATH（デフォルト: data/execution.pid）
    - CPU/MEMORY/DISK のしきい値（デフォルト値を設定）
    - KABUSYS_ENV の検証（development / paper_trading / live のみ有効）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- AI 関連（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - 指定ターゲット日の前日 15:00 JST 〜 当日 08:30 JST のニュースを対象にセンチメントを算出。
    - OpenAI（gpt-4o-mini）を JSON Mode で利用し、銘柄ごとに -1.0〜1.0 のスコアを生成。
    - バッチ処理: 最大 20 銘柄／リクエスト（_BATCH_SIZE=20）、1 銘柄あたり記事数上限／文字数上限（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）。
    - 再試行ロジック（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ、最大リトライ回数 _MAX_RETRIES=3）。
    - レスポンス検証: JSON 抽出、"results" の構造検証、未知コードの無視、スコアの数値化と ±1.0 クリップ。
    - DuckDB への書き込みは冪等（対象コードのみ DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - テスト容易性のため _call_openai_api を差し替え可能。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみを利用してルックアヘッドを防止。
    - マクロニュースは news_nlp のウィンドウ関数 calc_news_window に従って取得し、最大 20 記事までを LLM に投入。
    - OpenAI 呼び出しは再試行ロジック／5xx 判定を備え、全リトライ失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - 最終結果は market_regime テーブルに冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性を考慮し、_call_openai_api を差し替え可能に実装。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX（市場）カレンダーの管理ツール群を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar テーブルが未取得のときは曜日（週末）ベースでフォールバック。
    - カレンダーの夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得→保存、バックフィル、健全性チェックを実施。
    - 検索の最大探索範囲やバックフィル日数、サニティチェックの定数化。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを提供（取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - 差分取得、保存（idempotent）、品質チェック（quality モジュール連携）の設計方針を実装に反映。
    - デフォルトのバックフィル、カレンダー先読み等の方針を定義。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: 約1M/3M/6M リターン（営業日ベース）と MA200 乖離（ma200_dev）。
    - ボラティリティ / 流動性: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - バリュー: PER（price / EPS、EPS が 0/欠損なら None）、ROE（raw_financials から取得）。
    - DuckDB ベースの SQL 実装で、必要データ不足時は None を返す設計。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンをまとめて1クエリで取得。デフォルト horizons = [1,5,21]。入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関（ランクは同順位の平均ランクを採用）。有効レコードが 3 未満なら None。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

### 改善
- 全体設計上の安全策とテスト容易性
  - 各種アルゴリズムで datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を明示する形に統一（ルックアヘッドバイアス防止）。
  - OpenAI 呼び出しや外部依存部分は差し替え可能に実装してユニットテスト容易性を向上。
  - DuckDB 書き込み時の冪等性と部分失敗時の既存データ保護を考慮（DELETE → INSERT の設計）。

### 既知の注意点 / 制限
- OpenAI API のキーが未設定の場合、news_nlp.score_news / regime_detector.score_regime は ValueError を送出する。テスト時は api_key を引数で注入するか、環境変数 OPENAI_API_KEY を設定する必要あり。
- 一部 DuckDB バインド（executemany に空リスト不可）やバージョン差分に対するワークアラウンドが実装されているため、DuckDB バージョン依存の挙動に注意。
- raw_financials 由来の PBR・配当利回りなどは現バージョンでは未実装。

### セキュリティ / 操作上のヒント
- .env 自動読み込みを無効化したいテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OS 環境変数はデフォルトで保護され、.env による上書きを防ぐ挙動を持ちます（ただし .env.local は override=True の挙動で OS 環境変数で保護されたキーを除き上書きする設計）。

---

今後のリリース予定（例）
- ai: ニュース本文の詳細なトークン管理、モデル選択の柔軟化
- data: jquants_client の具体的実装と追加の品質チェックルール
- research: 追加ファクター・クロスバリデーションツールの提供

（注）本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして使う場合はリリース担当者による検証・追記を推奨します。