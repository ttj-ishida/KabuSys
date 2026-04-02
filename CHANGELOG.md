# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベースの実装内容から推測して作成しています（実際のコミット履歴ではありません）。

現在のバージョン
- [Unreleased]

[0.1.0] - 2026-04-02
Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、data / strategy / execution / monitoring を公開。
- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を自動ロードする仕組みを実装（プロジェクトルートを .git または pyproject.toml で判定）。
  - .env のパースロジックを独自実装（コメント、exportプレフィックス、シングル/ダブルクォート、エスケープ処理に対応）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - OS環境変数の保護（protected set を用いた上書き制御）に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）等のプロパティを公開。無効値は ValueError で検出。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約し、銘柄ごとに記事テキストをまとめて OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - チャンク単位のバッチ送信（最大20銘柄 / チャンク）、文字数・記事数のトリム処理、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密な検証とスコアの ±1.0 クリッピング。部分失敗時に既存スコアを保護するため、更新対象コードのみ DELETE→INSERT する冪等書き込み。
    - テスト容易性のため OpenAI 呼び出し部を差し替え可能（_call_openai_api を patch）。
    - タイムウィンドウ（JST ベース）計算ユーティリティ calc_news_window を提供（ルックアヘッドバイアスを防止）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - DuckDB からの過去データ参照は target_date 未満（排他）で行いルックアヘッドを防止。
    - OpenAI 呼び出しは独立実装でリトライ・エラー処理を実装。API 失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - market_regime テーブルへ冪等的に書き込むトランザクション処理を実装（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
- データプラットフォーム (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー（market_calendar）を使った営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった一貫した判定APIを提供。DB にデータがある場合は DB を優先、未登録日は曜日ベースでフォールバック。
    - カレンダー更新バッチ calendar_update_job を実装（J-Quants クライアント経由で差分取得 → 保存、バックフィル、健全性チェック含む）。
  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを定義し、ETL 実行結果（取得数／保存数／品質問題／エラー概要など）を表現。
    - pipeline モジュールの ETLResult を etl モジュールから再エクスポート。
    - 差分更新、バックフィル、品質チェックの設計方針を実装に反映（品質問題は収集して呼び出し元に委ねる設計）。
  - その他ユーティリティ
    - DuckDB に対するテーブル存在チェックや最大日付取得などの共通処理を実装。
- リサーチ（因子・特徴量探索） (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）、Value（PER, ROE）を SQL + DuckDB で計算する関数を提供。
    - データ不足時は None を返す（安全設計）。全関数は prices_daily/raw_financials のみ参照し、外部発注等の副作用はなし。
  - 特徴量探索ユーティリティ (src/kabusys/research/feature_exploration.py)
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（calc_ic）計算（スピアマンランク相関）、rank、factor_summary（count/mean/std/min/max/median）などを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - 研究向け API を __init__ で便利にエクスポート（zscore_normalize を data.stats から再利用）。
- テスト/運用に配慮した実装
  - API キーは関数引数で注入可能（api_key 引数）、未設定時は環境変数 OPENAI_API_KEY を参照。未設定なら ValueError を送出して明示的に失敗。
  - ルックアヘッドバイアス防止: 各 AI/研究処理は datetime.today()/date.today() を直接参照せず、target_date を明示的に渡す設計。
  - DuckDB の executemany に関する制約（空リスト不可）に配慮した実装。

Changed
- 該当なし（初回リリースにつき変更履歴なし）

Fixed
- 該当なし（初回リリースにつき修正履歴なし）

Deprecated
- 該当なし

Removed
- 該当なし

Security
- 該当なし

注記
- 本 CHANGELOG はソースコードから機能を推測して作成した要約です。実際のコミットログや設計ドキュメントを基にした変更履歴ではありません。実際の導入・運用に際しては、リリースノートへ追加の情報（既知の制約、互換性、マイグレーション手順、外部 API の利用条件等）を追記してください。