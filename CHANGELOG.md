CHANGELOG
=========

All notable changes to this project will be documented in this file.
このCHANGELOGは「Keep a Changelog」形式に準拠しています。  
（以下はソースコードから推測して作成した初期リリースの要約です）

[Unreleased]
------------

- なし

0.1.0 - 2026-04-03
------------------

Added
- 初回リリース: kabusys パッケージ（バージョン 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート。
- 環境設定管理モジュール (kabusys.config)
  - .env ファイルと環境変数の自動読み込み実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行う（__file__ 起点の探索で CWD に依存しない）。
  - .env パーサーは以下に対応:
    - export KEY=val 形式
    - シングル／ダブルクォート内のバックスラッシュエスケープ
    - クォート無しの行のインラインコメント認識（直前が空白・タブの場合）
  - Settings クラスで各種設定値をプロパティとして提供。主な環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - OPENAI_API_KEY（AI モジュールから参照）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - KABUSYS_ENV（development / paper_trading / live の検証あり）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証あり）
  - OS 環境の既存キーを保護する機構（protected set）による上書き制御。

- データプラットフォーム関連 (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル読み書き、営業日判定、next/prev/get_trading_days/is_sq_day）。
    - DB データがない/不完全な場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - 夜間バッチ calendar_update_job: J-Quants から差分取得、バックフィル、健全性チェック。
    - 探索の最大日数制限とログによるエラー検出。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果・品質問題・エラーログ等を構造化）。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）などの設計方針を反映。
  - jquants_client と組み合わせて idempotent（冪等）な保存を意図した設計（ON CONFLICT 相当の扱いを想定）。

- AI 関連 (kabusys.ai)
  - news_nlp:
    - raw_news と news_symbols を基に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - JSON Mode を用いた厳密な JSON 出力要求とレスポンスバリデーション実装。
    - バッチ処理（最大 20 銘柄 / コール）、1 銘柄当たり記事トリム（最大記事数・最大文字数）、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。
    - レスポンス整合性が取れた銘柄のスコアだけ ai_scores テーブルへ置換（DELETE → INSERT：部分失敗時に既存データを保護）。
    - API 呼び出し箇所はテストで差し替え可能（内部関数 _call_openai_api を patch する設計）。
    - 時間ウィンドウ計算（JST ベース: 前日15:00～当日08:30 = UTC で前日06:00～23:30）を提供（calc_news_window）。
    - フェイルセーフ: API 失敗や不正レスポンス時は個別銘柄をスキップし全体動作を継続。
  - regime_detector:
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出・保存。
    - prices_daily, raw_news, market_regime テーブルと連携。計算結果は冪等に market_regime に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは独立実装（news_nlp と内部関数を共有しない）で、リトライ・バックオフ・5xx 判定等を備える。API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - ルックアヘッドバイアス防止のため date 引数ベースで動作し、datetime.today() 等を参照しない設計。

- リサーチ / ファクター関連 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（200日移動平均）を銘柄別に計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。tru_range 計算で NULL 伝播を適切に扱う。
    - calc_value: raw_financials と prices_daily を組み合わせて PER、ROE を計算（EPS が 0/欠損の場合は PER を None）。
    - DuckDB を用いた SQL+Python 実装。外部 API/マーケット注文とは無関係に動作。
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得（LEAD を使用）。
    - calc_ic: スピアマン（ランク）相関で IC を計算。必要件数未満は None。
    - rank: 同順位は平均ランクで扱う実装（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median の統計要約を提供。
  - 研究ユーティリティは pandas 等に依存せず標準ライブラリ + DuckDB のみで設計。

Changed
- 初版のため該当なし（初期導入機能を列挙）。

Fixed
- 初版のため該当なし。

Security
- 環境変数読み込み時に OS 環境を保護する protected set を採用（意図せぬ上書きを防止）。
- OpenAI API キーは明示的に引数で注入可能（テストとセキュリティの両立）。

Design / Implementation Notes（コードから推測）
- DuckDB をコアのローカル分析 DB として利用（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等を想定）。
- 多くの処理で「ルックアヘッドバイアス防止」の方針が一貫して取り入れられている（date 引数ベース、datetime.today() を参照しない等）。
- OpenAI 呼び出しは JSON Mode（厳密な JSON）を前提にし、レスポンスの堅牢なバリデーションとフェイルセーフ（スコア=0.0 やスキップ）を採用。
- DB 書き込みは明示的なトランザクションと部分上書き（対象コードを限定して DELETE → INSERT）で部分的失敗時のデータ保護を図る。
- テストしやすさを意識した設計（API 呼び出し箇所を patch 可能にする等）。

Known issues / Limitations（ソースから推測）
- 現バージョンでは PBR や配当利回りなど一部バリューファクターは未実装。
- news_nlp / regime_detector は OpenAI API に依存するため API 利用料・レイテンシに注意が必要。
- DuckDB executemany に関する互換性を考慮した特殊処理が含まれている（空リストの扱いなど）。

Credits
- この CHANGELOG は提供されたソースコードの内容から自動推測して作成しています。実際のユーザードキュメントやリリースノートと差異がある場合は本ファイルを正式記録として扱う前にレビューしてください。