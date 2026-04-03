CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠しています。
詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-04-03
--------------------

Added
- 基本パッケージ初期リリース: kabusys 0.1.0
  - パッケージ概要: 日本株自動売買システムのコアライブラリ（モジュール: data, research, ai, config, 等）を提供。

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を追加（読み込み順: OS環境 > .env.local > .env）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - .env パーサ実装:
    - export KEY=val 形式対応、引用符内のエスケープ処理、行末コメント判定（引用なしでは直前に空白/タブがある '#' をコメントと解釈）。
    - 読み込み時に既存 OS 環境変数を保護する protected パラメータ。
  - Settings クラスを追加（settings インスタンスをエクスポート）。
    - J-Quants / kabu API / LINE / DB / 監視 / システム系の設定プロパティを提供。
    - デフォルト値・型変換・バリデーション（KABUSYS_ENV, LOG_LEVEL 等）を実装。
    - 必須項目取得用の _require() を実装（未設定時は ValueError）。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini / JSON mode）へバッチ送信して ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算 util（calc_news_window）。
    - バッチサイズ、記事数上限、文字数トリム、JSON レスポンス検証、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライを実装。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - DuckDB executemany の互換性を考慮した安全な DELETE → INSERT の置換ロジック（部分失敗時に他銘柄スコアを保護）。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込み。
    - マクロニュース抽出用キーワードリストを内蔵。
    - OpenAI 呼び出し・JSON パースのフェイルセーフ（API 失敗時は macro_sentiment = 0.0）。
    - DB 書き込みは冪等性を考慮した BEGIN / DELETE / INSERT / COMMIT を採用。失敗時に ROLLBACK を試行。

- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・平均売買代金・出来高比率を計算。
    - calc_value: raw_financials と当日の株価から PER / ROE を算出（EPS 不在は None）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、外部 API に依存しない。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。
    - rank / factor_summary: ランク化と基本統計量集計ユーティリティ。

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が存在する場合は DB 優先、未登録日は曜日ベースのフォールバック（週末 = 非営業日）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（取得件数・保存件数・品質チェック結果・エラー一覧を保持）。
    - 差分更新・バックフィル・品質チェックを行う方針を実装（詳細は pipeline モジュールの設計コメント参照）。
  - jquants_client との連携を想定した保存/取得処理をサポート（実体は data.jquants_client に依存）。

Changed
- 初回リリースのため "Changed" 項目はありません。

Fixed
- 初回リリースのため "Fixed" 項目はありません。

Security
- 初回リリースのためセキュリティ修正はありません。

Known issues / 注意事項
- DuckDB 互換性: executemany に空リストを渡すと失敗するバージョン対策が各所に実装されています。環境の DuckDB バージョンに注意してください。
- 日付参照: ML/分析系（news_nlp, regime_detector, research）は datetime.today()/date.today() に依存せず、明示的な target_date を受け取る設計です（ルックアヘッドバイアス防止）。
- タイムゾーン: raw_news.datetime は UTC 保存を前提とし、window 計算は UTC naive datetime を用います。タイムゾーン混在に注意してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション API）
  - OPENAI_API_KEY（AI 機能利用時。api_key を明示的に渡すことも可能）
  未設定時には関数が ValueError を投げます。
- OpenAI 呼び出しは gpt-4o-mini を仮定して JSON Mode を使用します。SDK の仕様差分に対して若干の耐性（status_code 有無の扱い等）を持たせていますが、将来の SDK 変更に注意してください。

開発者向けメモ
- テストしやすさ: OpenAI 呼び出し部分は内部で _call_openai_api を定義しており、unittest.mock.patch による差し替えが容易です。
- ロギング: 各モジュールは logger を利用して詳細な情報/警告/エラーを出力します。
- 冪等性: DB への書き込みは可能な限り冪等化（DELETE→INSERT または ON CONFLICT を想定）されています。

今後の予定（例）
- ai モジュールのモデル/パラメータ外部化（モデル名や重みを設定可能にする）
- ETL の細粒度監査ログ、UI/CLI ツールの追加
- テストカバレッジ強化と CI パイプライン整備

---
（補足: 本 CHANGELOG は提示されたコードベースの実装内容から推測して記載しています。実際のリリースノートとして利用する場合は、リリース日・バージョン確認および追加の変更点追記をお願いします。）