# Changelog

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリース日付はリポジトリ内のバージョン情報（kabusys.__version__ = "0.1.0"）と現状コードから推測して設定しています。

注意: 記載は提供されたコードベースの内容から推測して作成しています。

## [Unreleased]
- 未リリースの変更はありません。

## [0.1.0] - 2026-04-01

### 追加 (Added)
- パッケージの初期公開
  - パッケージバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - パッケージ外部公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env ファイルの自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の行パース機能を実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの取り扱いなど）。
  - Settings クラスを追加し、アプリケーションで必要な設定をプロパティ経由で取得可能に:
    - J-Quants / kabuステーション / Slack / データベースパス（DuckDB/SQLite）/監視閾値/システム環境（env, log_level 等）
    - 必須設定は未設定時に ValueError を投げる _require() 実装。

- ニュースNLP（AI）モジュール (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini / JSON Mode）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む機能を実装。
  - 処理フロー:
    - JST ベースのニュースウィンドウ（前日 15:00 〜 当日 08:30）を自動計算（calc_news_window）。
    - 銘柄ごとに最新記事を最大数／最大文字数でトリムしてバッチ送信（最大20銘柄/チャンク）。
    - レスポンスのバリデーション（JSON 抽出、results 構造検証、スコア型チェック、スコアの ±1 クリップ）。
    - 書き込みは冪等（DELETE → INSERT）で実施し、部分失敗時に既存データ保護を行う。
  - 再試行 / フェイルセーフ:
    - 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
    - API 失敗やレスポンス不正時はスキップして処理継続（フェイルセーフ）。
  - テスト容易性:
    - OpenAI 呼び出しを内部関数 _call_openai_api に抽象化し、unittest.mock.patch により差し替え可能に。

- 市場レジーム判定（AI + データ）モジュール (src/kabusys/ai/regime_detector.py)
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存する機能を実装。
  - 処理フロー:
    - DuckDB から過去データを参照して MA200 乖離を算出（ルックアヘッド回避のため target_date 未満データのみ使用）。
    - マクロキーワードでフィルタした最新ニュースを抽出し、OpenAI によりマクロセンチメント評価を取得（記事がない場合は LLM 呼び出しを行わず 0.0 とする）。
    - 取得値はクリップ・閾値判定を行いラベル化。DB への書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に実行。
  - OpenAI 呼び出しのリトライ、例外ハンドリング（RateLimitError, APIError, etc.）を実装。
  - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を発生。

- データプラットフォーム（Data）モジュール
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を基に営業日判定（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）を提供。
    - DB にデータがない場合は曜日ベース（土日休み）でフォールバックする設計。
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API から差分取得 → 保存。バックフィル、健全性チェックあり）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを追加し、ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。
    - 差分更新・バックフィル・品質チェック方針を実装するための基礎を追加。
    - ETLResult は辞書化（to_dict）して監査ログ等へ出力可能。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- 研究（Research）モジュール (src/kabusys/research/)
  - factor_research.py: モメンタム、ボラティリティ、バリュー等の定量ファクター計算を実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials の最新財務データを用いて PER、ROE を計算。
    - 各関数は DuckDB の prices_daily/raw_financials を参照し、結果を (date, code) をキーとする dict リストで返す。
  - feature_exploration.py: 将来リターン・IC・統計サマリー等を提供
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）までの将来リターンを一クエリで取得。
    - calc_ic: Spearman ランク相関（IC）を計算（有効データが 3 件未満の場合は None）。
    - rank: 平均順位（同順位は平均ランク）を返すユーティリティ。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージは主要関数を __all__ で公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- なし（初期バージョンのため既存からの変更はなし）。

### 修正 (Fixed)
- .env パーサーの堅牢化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープやインラインコメント処理などを含む詳細なパースを実装し、実運用での .env の柔軟な記述に対応。

- DuckDB 書き込みの互換性対策
  - executemany に空パラメータを渡さないガードを追加（DuckDB 0.10 の制約回避）。

### 既知の挙動 / 設計上の注意 (Notes)
- ルックアヘッドバイアス回避:
  - AI モジュール（news_nlp, regime_detector）、および研究系関数は内部で datetime.today()/date.today() を直接参照せず、明示的な target_date を受け取る設計。
- フェイルセーフ:
  - OpenAI API の失敗や不正レスポンスは基本的に例外で停止させず、0.0 やスキップで継続する実装。上位での判断に委ねる設計。
- 外部依存:
  - OpenAI SDK（OpenAI クライアント）と DuckDB に依存。外部 API 呼び出しはリトライ・バックオフを実装しているが、API キーの設定が必要。
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等は Settings で必須扱い（未設定時は ValueError）。
- テストの容易化:
  - OpenAI 呼び出しを内部ヘルパーに抽象化しており、モック化してテスト可能。

### セキュリティ (Security)
- 明示的なセキュリティ修正はなし。ただし API キーやシークレットは環境変数で管理する前提。

---

以上が、コードベース（提供されたソース）から推測した初回リリース（0.1.0）の変更点概要です。詳細な利用手順やマイグレーション、実装上の細かな振る舞いは各モジュールのドキュメンテーション（docstring）を参照してください。