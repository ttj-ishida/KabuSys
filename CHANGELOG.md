CHANGELOG
=========

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。
このファイルはコードベースから推測して作成した初期リリース向けの変更履歴です。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-01
--------------------

Added
- 初期リリース: kabusys パッケージを公開
  - パッケージバージョン: 0.1.0
  - パッケージ公開モジュール: data, research, ai, config（パッケージ __all__ に data, strategy, execution, monitoring を含む）
- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート
  - .env 行パーサー実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）
  - Settings クラスに各種設定プロパティを提供（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境判定・ログレベル検証 等）
  - 必須環境変数未設定時に ValueError を発生させる _require 実装
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価
    - バッチ処理（最大 20 銘柄/チャンク）、トークン肥大化対策（記事数・文字数トリム）、JSON レスポンス検証、スコアの ±1.0 クリップ
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ）、失敗時は該当チャンクスキップして継続
    - calc_news_window による JST/UTC ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）
    - テスト用に内部の OpenAI 呼び出しをモック可能に設計
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定・保存
    - OpenAI 呼び出しのリトライ/フォールバックや API エラー/パース失敗時の安全動作（macro_sentiment=0.0）を実装
    - DuckDB を用いた冪等な market_regime テーブル書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK ハンドリング）
- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫したロジック
    - JPX カレンダーを J-Quants から差分取得する夜間バッチ（calendar_update_job）とバックフィル／健全性チェック
  - ETL パイプラインインターフェース（kabusys.data.pipeline / etl）
    - ETLResult データクラスの導入（取得数・保存数・品質問題・エラーの集約）
    - 差分取得、backfill、品質チェックを考慮した設計（jquants_client および quality モジュールとの連携を前提）
    - data.etl で ETLResult を再エクスポート
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）
    - Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比）
    - Value（PER、ROE を raw_financials と prices_daily から計算）
    - DuckDB を用いた SQL ベースの実装、データ不足時は None を返す方針
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応・入力検証）
    - IC（Spearman のランク相関）計算（calc_ic）
    - ファクター統計サマリー（factor_summary）およびランク関数（rank）
  - research パッケージのエクスポートに zscore_normalize（kabusys.data.stats 由来）を含む
- 一貫した設計上の方針
  - ルックアヘッドバイアス防止: datetime.today()/date.today() の直接参照を避け、関数引数で日付を受け取る実装
  - テスト容易性: OpenAI 呼び出し箇所にモック差し替えの想定
  - DuckDB を前提とした SQL + Python ハイブリッドな実装
  - ログ出力（info/debug/warning/exception）を多用し状態追跡を容易に

Changed
- （初回公開のため該当なし）

Fixed
- （初回公開のため該当なし）

Security
- OpenAI API キー未設定時に明確な ValueError を発生させ、誤操作での無条件送信を防止

Known issues / Notes
- 一部モジュール（strategy, execution, monitoring）は __all__ に含まれているが、このスナップショットでは実装が提示されていません。実装は今後のリリースで追加予定です。
- DuckDB バインドや executemany の挙動（空リストの扱いなど）に関する互換性注意のため、空リストを渡す前にチェックする防御的実装が多数存在します。
- AI レスポンスの不確実性に対しては「失敗時にスキップして継続」「フェイルセーフ値を使用する」方針を採用しています（部分書き込み・部分失敗を許容）。
- calc_forward_returns の horizons 引数は 1〜252 の整数に制限しています。その他の入力は ValueError。

貢献・報告
- バグ報告や機能要望は issue を立てるか、リポジトリの CONTRIBUTING ガイドに従ってください。

--- 

（この CHANGELOG はコードベースの内容から推測して作成しています。詳細実装やリリース手順により正確なリリースノートを補完してください。）