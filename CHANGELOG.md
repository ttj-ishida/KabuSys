CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従って管理しています。

[Unreleased]
-------------

（なし）

0.1.0 - 2026-04-04
------------------

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点と設計上の注記を以下にまとめます。

Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定管理
  - 環境変数・.env ファイルを自動読み込みする設定モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートを __file__ を起点に .git または pyproject.toml で探索して特定。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - export KEY=val 形式やクォート内のエスケープ、行末コメントの扱いなどを考慮した .env パーサを実装。
    - 必須値取得用の _require()、各種設定プロパティ（J-Quants / kabu / LINE / DB パス / 監視しきい値 / 環境名・ログレベル検証等）を提供。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値制約と不正時の ValueError）。

- AI（NLP）モジュール
  - ニュースセンチメント解析モジュール news_nlp を追加（src/kabusys/ai/news_nlp.py）。
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのスコアを生成。
    - チャンク単位処理（デフォルト 20 銘柄 / チャンク）と 1 銘柄あたりの最大記事数／文字数制限を実装。
    - JSON Mode を用いた厳格なレスポンス検証ロジック（レスポンス復元処理含む）、スコアの ±1.0 クリップ。
    - API エラー（429・接続断・タイムアウト・5xx）に対する指数バックオフリトライ。API 失敗時は該当チャンクをスキップして処理継続するフェイルセーフ設計。
    - DuckDB（ai_scores への書き込み）向けに部分置換戦略（DELETE → INSERT）を採用し、部分失敗で他銘柄データを消さない設計。
    - DuckDB 0.10 の executemany が空リストを受け付けない点を考慮したガード実装。
    - テスト容易性のため _call_openai_api を patch 可能に実装。

  - 市場レジーム判定モジュール regime_detector を追加（src/kabusys/ai/regime_detector.py）。
    - 日次判定で ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して regime_label（bull/neutral/bear）を生成。
    - マクロニュースはニュース NLP のウィンドウ計算を利用し、マクロキーワードでフィルタしたタイトルのみを LLM に送信。
    - OpenAI 呼び出しは専用実装（news_nlp と内部関数を共有しない）で、リトライ・エラーハンドリング・JSON パースのフェイルセーフを備える。
    - DuckDB への冪等的書き込み（BEGIN / DELETE / INSERT / COMMIT）を採用。書き込み失敗時は ROLLBACK を試みる。

- データプラットフォーム（Data）モジュール
  - カレンダー管理モジュールを追加（src/kabusys/data/calendar_management.py）。
    - market_calendar を使った営業日判定（is_trading_day/is_sq_day）と next/prev/get_trading_days を提供。
    - market_calendar が未取得の場合は土日ベースでフォールバック。DB 登録値は優先する設計。
    - calendar_update_job を実装：J-Quants から差分取得し冪等保存、バックフィル／健全性チェックを実施。
  - ETL パイプラインとユーティリティを追加（src/kabusys/data/pipeline.py / etl.py）。
    - ETLResult dataclass を定義（取得数・保存数・品質問題・エラー一覧などを保持）。to_dict により品質問題をシリアライズ可能。
    - 差分取得、バックフィル、品質チェック方針を実装するための骨格を用意。
  - jquants_client 経由で外部 API を叩く設計（抽象化されたクライアントモジュールを想定）。

- リサーチ（研究）モジュール
  - ファクター計算群を追加（src/kabusys/research/）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR、ATR 相対値、20日平均売買代金、出来高比率等。
    - calc_value: raw_financials から取得した最新財務データと株価を組み合わせて PER/ROE を算出。
    - 共通方針として DuckDB 上の SQL + Python 実装、外部 API へはアクセスなし。
  - 特徴量探索モジュールを追加（feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出（リード関数による実装、ホライズン検証あり）。
    - calc_ic: Spearman（ランク）を用いた IC 計算（結合と数値フィルタリングを実装）。
    - rank / factor_summary: ランク化（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を提供。
    - 標準ライブラリのみで実装（pandas 等に非依存）。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を参照する方式。未設定時は ValueError を発生させ利用者に明示。  
- .env 自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策: news / regime / research の各処理は datetime.today() / date.today() に依存せず、呼び出し側から渡された target_date の前提でウィンドウ計算を行う実装。
- DuckDB 互換性: executemany の空リスト制約や日付型の扱いに注意した実装（_to_date 等）。
- フェイルセーフ: OpenAI API や外部 API の失敗はエラーでプロセス全体を停止させるのではなく、ログ出力してスキップまたはデフォルト値（例: macro_sentiment=0.0 / 空スコア）で継続する方針。
- テスト容易性: OpenAI 呼び出し箇所は内部関数を patch してモック可能に実装。

Acknowledgements / External deps
- OpenAI SDK（Chat Completions / JSON mode）を利用する想定。
- DuckDB を内部データベースとして利用。

今後の予定（例）
- strategy / execution / monitoring モジュールの具体的実装（現在はパッケージ公開のみ）。
- jquants_client の具象実装や API レート制御の強化。
- 単体テスト・統合テストの拡充（モックとテスト用データ準備）。

-----