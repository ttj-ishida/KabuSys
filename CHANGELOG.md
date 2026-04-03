Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

Unreleased
----------

0.1.0 - 2026-04-03
------------------

Added
- 初回公開リリース。
- パッケージ全体の骨格と主要機能を実装。
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml を探索）。CWD に依存しない探索実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - export KEY=val 形式・クォート・エスケープ・インラインコメント等に対応した .env パーサ実装。
  - 必須設定取得用 _require と Settings クラスを提供。主要環境変数:
    - OPENAI_API_KEY（OpenAI） / JQUANTS_REFRESH_TOKEN（J-Quants） / KABU_API_PASSWORD（kabuステーション）
    - KABUSYS_ENV（development|paper_trading|live）、LOG_LEVEL
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）、監視用パス（PID_FILE_PATH, KILL_FLAG_PATH） 等
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の値検証）。
- AI（自然言語処理）関連（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - JSON Mode を利用した厳密なレスポンス検証とスコアの ±1.0 クリップ。
    - 1チャンクあたり最大20銘柄、記事数・文字数制限（攻撃的肥大化対策）。
    - 429 / タイムアウト / ネットワーク断 / 5xx に対する指数バックオフでのリトライ。
    - 部分失敗が発生しても他銘柄の既存スコアを保護するよう、DELETE→INSERT の範囲絞りで冪等書き込み。
    - テスト時に _call_openai_api を patch できる設計。
  - regime_detector.score_regime
    - ETF 1321（Nikkei-linked ETF）の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出・保存。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）での macro_sentiment 評価。
    - LLM エラー時は macro_sentiment=0.0 とするフェイルセーフ。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等設計。失敗時は ROLLBACK を試行。
- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar を利用した営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - カレンダーデータが未取得のときは曜日ベース（土日除外）でフォールバック。
    - 夜間バッチ calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル、妥当性チェック付）。
  - pipeline / ETLResult（kabusys.data.pipeline / etl）
    - ETLResult データクラス（ETL の取得・保存数、品質チェック結果、エラー集約）。
    - 差分更新・バックフィル・品質チェックのための基盤設計を実装（jquants_client, quality モジュールと協調）。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティ。
- 研究用モジュール（kabusys.research）
  - factor_research
    - モメンタム（1m/3m/6m、ma200乖離）、ボラティリティ（20日ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials から計算。
    - データ不足時の None 扱い、DuckDB SQL を活用した高効率実装。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（Spearman）の calc_ic、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等外部依存を避け、標準ライブラリのみで実装。
- いくつかのユーティリティと設計方針の採用
  - ルックアヘッドバイアス防止: 各モジュールで datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る実装。
  - DuckDB に対する互換性配慮（executemany の空リスト回避など）。
  - OpenAI 呼び出しにおける堅牢なパースとレスポンス検証（JSON 抽出処理含む）。
  - テスト容易性を考慮した設計（API キー注入、内部 API 呼び出しの patch 対応など）。

Fixed
- OpenAI・ネットワークエラー時の挙動を明確化。API 失敗時に例外を上位へ上げずフェイルセーフ（0.0 戻し）で継続する箇所を明示的に実装（news_nlp, regime_detector）。
- DuckDB に対するロールバック失敗時のログ出力改善。

Security
- .env 自動読み込み時、既存 OS 環境変数は保護（.env.local は override=True でも OS 環境変数を上書きしない）。
- 環境変数未設定時の ValueError により、重要な認証情報が不足したまま稼働することを防止。

Notes / その他
- OpenAI モデル: gpt-4o-mini を利用（JSON Mode 想定）。
- 必要な外部依存（例）: duckdb, openai（環境によって適切なバージョンをインストールしてください）。
- Python の型表記（X | Y）を使用しているため、Python 3.10 以上を想定しています。
- 現在の実装は本番発注（execution）モジュールやモニタリング周辺の公開 API はパッケージに含まれますが、本リリースではデータ取得・NLP・研究機能・カレンダー管理・ETL 基盤に重点を置いています。
- 将来のリリースで: 監視（monitoring）・実行（execution）・追加の ETL 正常性チェック等の拡張を予定。

既知の制約
- news_nlp / regime_detector の LLM 呼び出し結果は LLM の出力品質に依存するため、誤った JSON を返すケースに対する耐性は実装しているが、根本的な誤出力を完全に排除するものではありません。
- DuckDB 実装のバージョン差分（配列バインド等）により一部 SQL バインディングが環境依存になる可能性があるため、ETL 側で互換性対策を行っています。

以上

