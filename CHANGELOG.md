# CHANGELOG

すべての変更は Keep a Changelog 様式に従います。  
このファイルはリポジトリ内のコード内容から推測して作成した初期の変更履歴です。

全般的な方針:
- 日付は本ファイル作成日（2026-03-29）をリリース日として記載しています。
- エントリは主に追加（Added）、変更（Changed）、修正（Fixed）、セキュリティ（Security）のカテゴリで整理しています。

## [0.1.0] - 2026-03-29

### Added
- 初期パッケージリリース: kabusys
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - パッケージ外部公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。

- 環境/設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む。
  - .env パーサーを実装（コメント、export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
  - OS 環境変数を保護する protected set を使った上書き制御を実装。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティを定義。必須項目は未設定時に ValueError を送出。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）でセンチメントをスコア化して ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、記事数/文字数トリム（最大記事数・最大文字数）、JSON Mode 応答の検証ロジックを実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、応答バリデーションおよび部分書き込み（部分失敗時に既存データを保護）を実装。
    - calc_news_window 関数で JST ベースのニュース収集ウィンドウ計算を提供（ルックアヘッドバイアスを避ける設計）。
    - 公開 API: score_news(conn, target_date, api_key=None) を提供。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロキーワードによるニュース抽出、OpenAI（gpt-4o-mini）呼び出し、リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - データベースへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）で market_regime テーブルを更新。
    - 公開 API: score_regime(conn, target_date, api_key=None) を提供。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基に営業日判定とヘルパー（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job(conn, lookahead_days=...) を実装。J-Quants クライアント経由で差分取得・冪等保存。
    - カレンダーデータ未取得時の曜日ベースのフォールバックや、最大探索日数制限で安全性を確保。

  - ETL / パイプライン（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返却可能に。
    - 差分更新、バックフィル、品質チェックとの連携を想定した設計（J-Quants クライアントとの連携を前提）。
    - etl モジュールで ETLResult を再エクスポート。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB を用いた SQL/ウィンドウ関数で実装。部分データ不足時は None を返す。
    - 設計上、prices_daily / raw_financials のみ参照し、実口座操作は行わない。
    - 公開 API: calc_momentum, calc_volatility, calc_value。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（スピアマンρ）計算 calc_ic、ランク変換 rank、統計サマリー factor_summary を実装。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB クエリで完結。

- 内部ユーティリティ
  - DuckDB 接続を前提に動作する多数のユーティリティと安全対策（例: executemany に空リスト渡さないなど）を実装。
  - LLM 呼び出し箇所はテスト容易性のため内部の _call_openai_api を参照して差し替え可能。

### Changed
- 設計面の重要な決定と実装方針（ドキュメント化）
  - ルックアヘッドバイアス防止: 日付処理で datetime.today() / date.today() を直接参照しない設計（スコア計算は外部から target_date を受け取る）。
  - データベース書き込みは冪等化（DELETE→INSERT や ON CONFLICT）を基本とし、部分失敗時に既存データを保護する方針を採用。
  - 外部依存を最小化: リサーチ系は標準ライブラリのみで実装（pandas 等に依存しない）。

### Fixed / Robustness improvements
- LLM 応答の堅牢化
  - JSON Mode であっても前後に余計なテキストが混ざるケースに備え、最外側の {} を抽出してパースを試みるロジックを追加（news_nlp）。
  - レスポンスのバリデーションを厳密化（results キー・型チェック、スコア数値化、未知コードの無視など）。

- フェイルセーフ挙動の導入
  - OpenAI 呼び出しでの失敗（429/ネットワーク/タイムアウト/5xx）に対してリトライ（指数バックオフ）を実装し、最終的に失敗した場合は安全側のデフォルト値（macro_sentiment=0.0、ma200_ratio=1.0、該当銘柄スキップ）にフォールバックして処理を継続する設計。
  - DuckDB のバージョン差異（executemany に空リスト不可）に対応するため、空チェックを入れてから executemany を実行。

- 環境変数周りの堅牢化
  - 必須トークン未設定時に分かりやすい ValueError を返す（OpenAI / Slack / J-Quants / kabu API 等）。
  - .env 読み込み失敗時は警告を出力して処理を続行（読み込み失敗を致命にしない）。

### Security
- 環境変数の扱い
  - OS 環境変数を保護する protected set を導入し、.env や .env.local による上書きを制御。
  - 自動 .env ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供し、テストや安全な実行環境での切り替えを容易化。
  - 必須のシークレット（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）が未設定の場合に早期に検出する実装。

### Known limitations / Notes
- OpenAI SDK 依存: OpenAI の挙動や例外クラスに依存しているため、SDK の将来の変更には注意が必要（例: APIStatusError / status_code の扱いなど）。
- 一部 SQL バインドや DuckDB の挙動はバージョン差に依存するため、運用時は DuckDB バージョン互換性を確認すること。
- ai_scores / market_regime 等のテーブルスキーマは本履歴には含まれていません。DB スキーマは別途管理される想定です。

---
（以上がコードベースの初期リリース v0.1.0 に相当する変更点の要約です。）