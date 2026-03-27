CHANGELOG
=========

すべての重要な変更点を記録します。本ドキュメントは「Keep a Changelog」形式に準拠しています。

フォーマット:
- セマンティックバージョニングに従います。
- 各リリースは日付付きで記載します。
- セクションは Added / Changed / Fixed / Security を基本とします。

Unreleased
----------
（なし）

0.1.0 - 2026-03-27
-----------------

初回公開リリース。日本株自動売買/データ基盤のコア機能群を実装しました。
以下はコードベース（src/kabusys 以下）の主要な追加・設計上の特徴です。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンを __version__ = "0.1.0" として定義。
  - サブパッケージ公開: data, research, ai, 等を __all__ でエクスポート。

- 環境設定/設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（優先順位: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメントの扱い（クォートの有無で異なる挙動）。
  - 既存 OS 環境変数を保護する protected ロジック（.env 上書き制御）。
  - 必須環境変数取得用の _require ユーティリティ。
  - Settings クラスで各種設定プロパティを提供（J-Quants / kabu ステーション / Slack / DB パス / 環境・ログレベル判定等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（有効値チェック）。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメント（news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）に JSON Mode で投げて銘柄別センチメント（ai_scores）を生成・保存する処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事選定、1銘柄あたりの最大記事/文字数トリム、バッチ処理（最大 20 銘柄／呼び出し）。
    - レスポンスバリデーション、数値スコアの ±1.0 クリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ実装。
    - DuckDB への冪等書き込み（DELETE→INSERT のトランザクション）により部分失敗時の保護。
    - テスト易化のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定・保存。
    - マクロセンチメントは別途 news_nlp の記事集計関数 calc_news_window を利用して取得した記事タイトルを OpenAI に投げて評価。
    - API エラー時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック保護を実装。
    - LLM 呼び出しは独立実装とし、モジュール間の過度な結合を回避。

- Data / ETL / カレンダー（src/kabusys/data）
  - calendar_management
    - JPX マーケットカレンダー管理機能（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar テーブルがない場合の曜日ベースのフォールバックを実装。
    - calendar_update_job: J-Quants API からの差分取得・バックフィル（直近 N 日）・保存（冪等）処理を実装。健全性チェック（将来日付の異常検出）を実装。
  - pipeline / ETLResult（src/kabusys/data/pipeline.py, etl.py）
    - ETL の結果を表すデータクラス ETLResult を提供（取得数、保存数、品質問題、エラー一覧などを含む）。
    - 差分更新・バックフィル・品質チェックを行う ETL パイプライン設計に沿ったユーティリティ群を実装。
    - DB 最大日付取得やテーブル存在判定などのユーティリティを実装。

- Research（src/kabusys/research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR・相対 ATR）、流動性（平均売買代金・出来高比率）、バリュー（PER, ROE）などのファクター計算関数を実装。
    - DuckDB の SQL を活用し、prices_daily / raw_financials のみ参照する安全設計。
    - 出力は (date, code) をキーとする dict のリスト。
  - feature_exploration
    - 将来リターン calc_forward_returns（ホライズン指定可）、IC 計算 calc_ic（Spearman のランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas等外部依存を避け、標準ライブラリのみで実装。

- 共通設計方針・実装上の特徴
  - DuckDB を主要なローカル分析 DB として想定し、SQL と Python の組み合わせで実装。
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を API の内部で使わない（外部から target_date を与える設計）。
  - LLM 呼び出しに対して堅牢なエラーハンドリング（リトライ、5xx と非5xx の差別化、レスポンスパース失敗時フォールバック）。
  - テスト容易性: LLM 呼び出し部分は patch で差し替え可能にしている箇所がある（_call_openai_api 等）。
  - DB 書き込みはできるだけ冪等化（DELETE → INSERT、ON CONFLICT など）しており、部分失敗時の既存データ保護を考慮。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の扱いに配慮:
  - OS 環境変数が .env によって上書きされないよう protected キーセットを利用。
  - OpenAI API キー取得時に未設定なら ValueError を投げ、明示的に扱う設計とした。

Internal / Developer notes
- .env ローダーはプロジェクトルートを __file__ の親ディレクトリから探索（.git または pyproject.toml による判定）するため、CWD に依存しない。
- DuckDB executemany の挙動（空リスト不可）に対応したガードを実装。
- OpenAI SDK の例外種類や将来の SDK 変更に備え、status_code の取得に getattr を使う等、堅牢性を高めている。
- 設計ドキュメント（コメント）で各モジュールの処理フローや設計方針を詳細に記述。

破壊的変更（Breaking Changes）
- なし（初回リリース）

今後の予定（提案）
- LLM モデル選択やプロンプトのチューニング設定を外部化（設定から変更可能に）する。
- ETL の監査ログ/メトリクス出力や retry/backoff を共通ユーティリティ化。
- research モジュールの並列化・最適化や pandas 連携オプションの追加。
- 単体テスト・統合テストの充実（特に LLM 呼び出しまわりはモック化しての網羅が必要）。

-----

注: 本 CHANGELOG は提示されたソースコード（src/kabusys 以下）の実装内容・コメント・設計意図から推測して作成しています。実際の変更履歴やリリース日付はリポジトリ運用方針に合わせて調整してください。