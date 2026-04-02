Keep a Changelog 準拠 — 変更履歴 (日本語)
====================================

このファイルは、リポジトリ内の現行コードベースの内容から推測して作成した CHANGELOG です。実装された主要機能、設計上の注意点、既知の挙動を日本語でまとめています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-04-02
------------------

Added
- パッケージ全般
  - 初期リリース (version 0.1.0) として主要モジュール群を追加。
  - パッケージルート: src/kabusys/__init__.py （__version__ = "0.1.0"）。
  - パッケージ公開 API に data, strategy, execution, monitoring を含めるエクスポートを定義。

- 環境設定 (src/kabusys/config.py)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供（テスト用途）。
  - .env パーサーの強化:
    - export KEY=val 形式対応、コメント行／空行の無視。
    - シングル/ダブルクォートとバックスラッシュのエスケープ処理対応。
    - クォート無しの行に対するインラインコメント認識（直前が空白/タブの場合）。
  - .env の読み込みで OS 環境変数を保護する protected set を導入し、.env.local による上書きや上書き制御を実現。
  - Settings クラスを提供し、J-Quants / kabuステーション API / Slack / データベース / 監視 / システム設定を環境変数から読み出すプロパティを実装。
    - 必須キーは _require() で明示的にチェック（未設定時は ValueError）。
    - KABUSYS_ENV の許容値検証（development / paper_trading / live）。
    - LOG_LEVEL の許容値検証。
    - Path 型プロパティ（duckdb, sqlite, pid）・数値閾値プロパティ（CPU/MEM/DISK）を提供。

- データプラットフォーム (src/kabusys/data)
  - calendar_management モジュール
    - JPX マーケットカレンダー管理（market_calendar テーブル操作）と夜間更新ジョブ（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - market_calendar が存在しない場合は曜日ベースのフォールバック（週末を非営業日）を使用し、一貫した挙動を維持。
    - 最大探索日数などの安全制約（_MAX_SEARCH_DAYS, _SANITY_MAX_FUTURE_DAYS 等）を実装。
    - J-Quants クライアント（jquants_client）経由での取得と冪等保存をサポート、バックフィル日数を考慮。

  - ETL / pipeline モジュール
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー一覧を含む）。
    - 差分取得・バックフィル・品質チェックの設計方針を実装（品質チェックの問題を収集して呼び出し元で判断する方式）。
    - DuckDB の制約を考慮（executemany に空リスト不可など）した実装注意点を反映。

  - etl モジュールは pipeline.ETLResult を再エクスポート。

- AI モジュール (src/kabusys/ai)
  - news_nlp モジュール
    - ニュース記事（raw_news / news_symbols）を銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で計算（UTC naive datetime で返す）。
    - バッチ処理 (最大 _BATCH_SIZE = 20 銘柄)・1銘柄あたりの記事数上限・文字数トリムを実装して API 負荷を制御。
    - レート制限 (429), ネットワーク断, タイムアウト, 5xx エラーに対する指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション実装:
      - JSON モードでも前後テキストが混ざる場合の復元ロジック。
      - results 配列の構造検査、未知コードの無視、スコアを ±1.0 にクリップ。
    - テスト容易性: _call_openai_api を patch してモック可能。
    - API キーが未設定のときは ValueError を送出。

  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) とマクロニュースの LLM センチメントを合成して日次市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200_ratio の計算は target_date 未満データのみを使用してルックアヘッドを排除。
    - マクロ記事抽出（キーワードベース）と LLM 呼び出し（gpt-4o-mini）を行い、重み付け合成（70% MA, 30% Macro）でスコアを算出し clip。
    - OpenAI API エラー時のフェイルセーフ（macro_sentiment=0.0）とリトライ、ログ出力を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。

- Research モジュール (src/kabusys/research)
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20日 ATR、相対ATR (atr_pct)、20日平均売買代金、出来高比率を計算。入力データ不足判定。
    - calc_value: raw_financials から最新財務を結合し PER / ROE を算出（EPS=0 や欠損時は None）。
    - DuckDB を用いた SQL + Python 実装。外部 API に依存しない。

  - feature_exploration モジュール
    - calc_forward_returns: target_date から指定 horizon（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: factor_records と forward_records を code で結合し、スピアマンのランク相関（IC）を計算。有効レコード < 3 の場合は None。
    - rank: 同順位は平均ランクを返す安定実装（round(v,12) による丸めで ties 判定を安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出（None 値除外）。
  - research.__init__ で主要関数をエクスポート。

Changed
- 実装設計上の注意（全モジュール横断）
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接参照しない設計を採用（target_date パラメータ駆動）。
  - DuckDB のバージョンや制約（executemany の空リスト等）を考慮した実装上のガードを追加。
  - API 呼び出しに関する挙動は「フェイルセーフで継続」するポリシー（例外を上位に投げない箇所がある）を採用。ロギングで検知可能。

Fixed
- レスポンスパースや外部 API の失敗時の挙動を明確化:
  - OpenAI API の JSON パース失敗や API エラー時はログ出力してゼロ相当またはスキップで継続（例外を潰す設計、ただし API キー未設定は例外）。
  - regime_detector と news_nlp の両方で同様の retry/backoff 戦略を統一的に扱う設計に。

Security
- 機密情報取り扱い:
  - OpenAI API キーや各種トークンは Settings 経由で環境変数から取得。未設定時は明示的にエラーを出す箇所があるため、運用時に環境変数管理が必須。

Deprecated
- なし

Removed
- なし

Notes / Known limitations
- strategy / execution / monitoring パッケージは __all__ に含まれるが、この差分にはそれらの実装ファイルが含まれていません。発注や実行系の実装は別途存在する想定です。
- OpenAI との統合は gpt-4o-mini + JSON mode 前提で実装しているため、将来モデルや API の大きな変更があれば呼び出しラッパーやレスポンス処理の更新が必要です。
- DuckDB の型・バインド挙動（特に配列や executemany の空リスト）に依存する実装箇所があるため、DuckDB バージョン変更時は動作確認を推奨します。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar の返り値や例外に依存するため、外部クライアント実装に合わせてテストしてください。

お問い合わせ / 貢献
- 仕様やコードの意図に関する不明点はソース内の docstring とログメッセージを参照してください。テストや追加機能の提案は PR を通じて歓迎します。