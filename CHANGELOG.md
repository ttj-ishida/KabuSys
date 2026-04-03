Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]


## [0.1.0] - 2026-04-03

初回リリース（初期実装）。以下の主要機能・モジュールを実装しています。

Added
-----
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" に設定。主要サブパッケージ（data, research, ai, execution, monitoring, strategy 等の意図）を公開するための __all__ を定義。

- 環境変数 / 設定管理（kabusys.config）
  - プロジェクトルート検出：.git または pyproject.toml を起点に自動でプロジェクトルートを特定するユーティリティを追加。
  - .env 自動読み込み：OS環境変数 > .env.local > .env の優先順位で自動ロード。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサの強化：export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの許容などをサポート。
  - Settings クラス：J-Quants / kabuステーション / LINE / DB パス / 監視パラメータ / ログレベル / 環境（development / paper_trading / live）などのプロパティを提供。必須項目は未設定時に ValueError を送出。
  - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL 等）とデフォルト値を用意。

- AI モジュール（kabusys.ai）
  - ニュース NLP（news_nlp.score_news）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ定義（JST基準で前日 15:00 ～ 当日 08:30 を UTC に変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄当たり最大記事数・文字数トリム、リトライ（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ）実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト・code・score 検証）、スコアを ±1.0 にクリップ。
    - 書き込みは冪等化（DELETE → INSERT をトランザクション内で実行）。部分失敗時に既存データを過度に消さない設計（affected codes のみ置換）。
    - API 呼び出し部はテストで差し替え可能（_call_openai_api の patch を想定）。

  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム ('bull' / 'neutral' / 'bear') を算出して market_regime テーブルへ保存。
    - マクロニュースは事前定義キーワードでフィルタし、最大記事数を制限して LLM に送信。
    - OpenAI 呼び出しでのリトライ / レスポンス解析失敗は macro_sentiment=0.0 にフォールバック（例外を投げず継続）。
    - データベース書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）かつ失敗時に ROLLBACK を試行しログを記録。

- 研究・ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily 参照）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS が 0 または欠損の場合は None）。
    - DuckDB のウィンドウ関数を利用した SQL ベースの実装で、外部 API にはアクセスしない設計。
  - feature_exploration モジュール:
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。データ不足時（有効レコード < 3）は None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を算出。
    - 外部依存を排し標準ライブラリ + DuckDB のみで実装。

- データ基盤（kabusys.data）
  - calendar_management:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API を実装。
    - market_calendar が未登録の場合は曜日（平日）ベースでフォールバック。DB 登録値があれば優先。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィルと健全性チェックを実装）。
    - 最大探索日数や先読み / バックフィル日数等の安全策を導入（過度なループや将来日付の異常を検出してスキップ）。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得数 / 保存数 / 品質問題 / エラー等の集約）。
    - ETL の差分取得、保存（jquants_client の save_* を使用して idempotent に保存）、品質チェック呼び出しを想定する設計。
    - DuckDB 互換性（テーブル存在チェック等）と backfill のデフォルト動作を定義。

- DuckDB 互換性考慮
  - executemany に空リストを与えられない DuckDB 0.10 の挙動を考慮したガードを実装（空の場合は実行をスキップ）。

Security
--------
- 環境変数読み込み時、OS 環境変数は protected として .env による上書きをデフォルトで防止（.env.local で上書き可能）。
- OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等の必須トークンは未設定の場合 ValueError を投げ、誤った運用を防止。

Fixed / Robustness
------------------
- OpenAI API 呼び出しでのネットワーク障害やレート制限、5xx を考慮したリトライと指数バックオフを導入。最終的に失敗した場合は例外を上位に投げずフェイルセーフなデフォルト（例: macro_sentiment=0.0）で処理を継続する箇所がある。
- DB 書き込み時に例外発生した場合は ROLLBACK を試み、さらに ROLLBACK 自体の失敗は警告ログに記録。
- ルックアヘッドバイアス対策として、全ての日付処理は外部から渡される target_date を起点に行い、内部で date.today() / datetime.today() を参照しない設計を徹底。

Known issues / Notes
--------------------
- 本リリースでは OpenAI SDK（gpt-4o-mini）への依存があり、API キー（OPENAI_API_KEY）の設定が必須な処理がある。API キー未設定時は該当 API 呼び出し前に ValueError を返す。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、意図的に共有しない（モジュール結合を低減する設計）。
- ai モジュールの出力は外部 API の品質に依存するため、レスポンスのパース失敗や非期待応答はログに記録してスキップ／フォールバックする実装になっている。
- J-Quants クライアント（kabusys.data.jquants_client）は外部実装を想定。ETL やカレンダー更新は外部 API 呼び出しに依存するため、実行環境での適切なクライアント実装が必須。

その他
-----
- ドキュメントの一部（モジュール先頭の docstring）に設計方針や処理フローを詳細に記載。ユニットテストでの差し替えポイント（_call_openai_api など）を明示しておりテスト容易性を考慮。

---

今後の予定（例）
- 監視 / 実行 / 戦略モジュールの公開API詳細化および CLI / サービス化。
- ai モデル・プロンプトの改良と評価指標の自動集計。
- ETL のスケジューリング・監査ログ強化および品質チェックのルール追加。

（以上はコードベースの内容から推測して作成しています。必要に応じて差分や日付を調整してください。）