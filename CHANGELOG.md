# Changelog

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

最新リリース
=============

Unreleased
----------

（次回リリース用の未リリース項目があればここに記載します）

リリース履歴
===========

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初版を公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本的なモジュール構成を導入
  - kabusys.config: 環境変数 / .env 読み込みおよび設定管理
    - .git または pyproject.toml を基準にプロジェクトルートを自動検出して .env/.env.local を読み込む自動ロード機能（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - export KEY=val 形式やシングル/ダブルクォート、インラインコメント等に対応する .env パーサ実装。
    - 必須設定取得用の _require()、Settings クラス（J-Quants / kabuステーション / Slack / DB パス / ログレベル / 環境判定プロパティ等）を提供。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

  - kabusys.ai
    - news_nlp: ニュース記事に対するセンチメントスコアリング
      - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄毎のスコアを ai_scores テーブルへ書き込み。
      - JST の時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
      - バッチサイズ、記事上限、文字トリム、JSON Mode を使った応答検証、±1.0 でのクリッピング、部分成功時の部分更新（DELETE → INSERT）などを実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライを実装。
      - テスト容易性のため OpenAI 呼び出し関数を patch で差し替え可能に設計。

    - regime_detector: 市場レジーム判定
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で ('bull'/'neutral'/'bear') 判定。
      - prices_daily / raw_news を参照し ma200_ratio 計算、マクロ記事抽出、OpenAI による macro_sentiment 評価（gpt-4o-mini）、スコア合成、market_regime テーブルへの冪等書き込みを実装。
      - API エラー時のフェイルセーフ（macro_sentiment=0.0）やリトライ、JSON パースの堅牢化を実装。
      - LLM 呼び出しは news_nlp と独立した実装でモジュール結合を避ける設計。

  - kabusys.data
    - calendar_management: JPX 市場カレンダー管理
      - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - DB 登録値優先、未登録日は曜日ベースのフォールバック、探索上限 (_MAX_SEARCH_DAYS) による安全策を実装。
      - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアントから差分取得→保存（冪等）→バックフィル／健全性チェックを行う。

    - pipeline / etl: ETL パイプライン基盤
      - ETLResult dataclass を導入（取得件数、保存件数、品質検査結果、エラー一覧を保持）。
      - 差分取得、バックフィル、品質チェック設計に対応するユーティリティ群（_get_max_date など）。

    - etl を公開するための kabusys.data.etl モジュール（ETLResult を再エクスポート）。

  - kabusys.research
    - factor_research: ファクター計算（Momentum / Value / Volatility / Liquidity）
      - calc_momentum: mom_1m/3m/6m、ma200_dev（データ不足時は None）
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
      - calc_value: PER / ROE を raw_financials と prices_daily から算出
      - DuckDB SQL を活用し、外部 API に依存しない純粋分析関数として実装
    - feature_exploration: 将来リターンとファクター評価
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
      - calc_ic: Spearman（ランク相関）による IC 計算（レコード数不足時は None）
      - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出
      - rank: 同順位は平均ランクとするランク関数
    - zscore_normalize は kabusys.data.stats から再エクスポート

General / Design decisions
- ルックアヘッドバイアス防止: datetime.today() / date.today() を関数内部で参照せず、target_date 引数で時刻窓を決定する設計を徹底。
- DuckDB を主たるストレージとして想定（DuckDB 接続を引数で受ける API）。
- DB 書き込みは冪等（DELETE → INSERT や ON CONFLICT 相当）・トランザクション管理（BEGIN / COMMIT / ROLLBACK）で保護。
- 外部 API 呼び出し（OpenAI / J-Quants）はリトライやフェイルセーフを備え、部分失敗が他データを破壊しないように設計。
- テスト容易性のため、OpenAI 呼び出し箇所は内部関数を patch で差し替え可能に実装。
- ロギングを多用し、警告・情報ログで動作状況やフェイルオーバーを可視化。

Documentation / Examples
- config モジュールに settings の使用例を docstring で記載。
- 各モジュールに処理フロー、設計方針、戻り値の仕様、例外動作等を豊富に docstring として記載。

Known limitations
- 一部機能は外部サービスの API キー（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN など）に依存。テスト時は環境変数または関数引数で注入が必要。
- 現フェーズでは PBR や配当利回りなどの一部バリューファクターは未実装。
- ai モジュールは gpt-4o-mini（JSON mode）を想定した実装。将来モデル仕様の変化に合わせた調整が必要になる可能性あり。
- パッケージの __all__ には "execution", "monitoring" が含まれるが、これらの具象実装は本リリース中では限定的、または別途追加される想定。

Security
- 本リリースで報告済みのセキュリティ修正はありません。

Credits
- 初期実装（0.1.0）の各モジュールは設計方針に沿って実装されました。

---

注: 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴や変更内容に基づく正式なログ作成時には各コミットメッセージや PR を参照してください。