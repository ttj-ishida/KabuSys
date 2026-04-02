CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and uses Semantic Versioning.

[Unreleased]
------------

- なし（初回リリース）

[0.1.0] - 2026-04-02
-------------------

Added
- パッケージ初期リリース。主要コンポーネントを実装。
  - kabusys.config
    - .env ファイルと環境変数の自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml）。
    - .env パーサーの実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
    - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB /監視 /システム設定のプロパティを提供。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値チェック）。
  - kabusys.ai.news_nlp
    - ニュースの NLP（センチメント）スコアリングパイプラインを実装。
    - タイムウィンドウ計算（JSTベース → DBは UTC 想定）。
    - raw_news と news_symbols を集約し、銘柄毎に最大記事数・文字数でトリムして OpenAI にバッチ送信。
    - gpt-4o-mini（JSON Mode）を想定した呼び出し／レスポンス検証ロジックを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライを実装。
    - レスポンスのバリデーション（resultsキー、型チェック、未知コード無視、スコアクリップ）。
    - DuckDB へ安全に置換（DELETE → INSERT）するロジックを実装し、部分失敗時に他のコードの既存データを保護。
    - 単体テスト容易化のため _call_openai_api を差し替え可能に設計（unittest.mock.patch を想定）。
  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次市場レジーム判定（bull/neutral/bear）を実装。
    - DuckDB からの価格取得、マクロキーワードでの raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）を実装。
    - API失敗時は macro_sentiment=0.0 のフェイルセーフを採用。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - kabusys.research
    - ファクター計算群を実装（research パッケージ公開 API を整備）。
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の計算を実装。データ不足時の None ハンドリング。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を実装。
      - calc_value: raw_financials と株価を組み合わせて PER / ROE を計算（EPS=0/欠損時は None）。
    - feature_exploration:
      - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する SQL 実装。
      - calc_ic: スピアマンのランク相関（IC）計算を実装（結合/除外/最小件数チェックあり）。
      - rank: 同順位は平均ランクを返すランク化ユーティリティを実装（丸めによる ties 対策あり）。
      - factor_summary: 基本統計量（count/mean/std/min/max/median）を実装。
  - kabusys.data
    - calendar_management:
      - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、バックフィル・健全性チェックを実装。
      - calendar_update_job: J-Quants から差分取得して冪等保存するバッチ処理を実装（バックフィルと健全性チェック含む）。
    - pipeline / etl:
      - ETLResult データクラスを公開して ETL 処理結果を表現。
      - pipeline モジュールに差分取得・保存・品質チェックを想定した骨組みを実装（jquants_client と quality モジュールを利用）。
      - ETL 実行に関する backfill やカレンダー先読みなどの運用パラメータを実装。
    - jquants_client との連携を前提とした設計（クライアント実装は別モジュール）。
  - パッケージ公開情報
    - kabusys.__init__ にて __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

Changed
- 設計方針の明示的適用:
  - すべての AI / データ処理モジュールで datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。
  - DuckDB の executemany の制約を考慮した空リストチェックを導入（互換性向上）。
  - OpenAI 呼び出しの失敗時に例外を上位へ即時伝播させない「フェイルセーフ」ポリシーを採用し、処理を継続できる設計に統一。

Fixed
- .env 読み込みでの実務的なパース不具合を解消:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ、コメントの判定を改善。
- AI 結果パースの堅牢化:
  - JSON mode でも前後に余計な文字列が混ざるケースを想定して最外の {} を抽出して復元する処理を追加。
- OpenAI API エラー処理:
  - APIError（ステータスコードを持つ場合）の 5xx 判定とリトライ処理を安全に扱うよう改善。
- calendar_update_job の健全性チェック追加:
  - market_calendar の last_date が極端に未来（1年以上先等）の場合はスキップしてログ出力。

Notes / Known limitations
- calc_value の一部ファクター（PBR、配当利回り）は現バージョンでは未実装（ドキュメント注記あり）。
- 実行環境は DuckDB と OpenAI SDK（OpenAI Python クライアント）を想定。jquants_client と quality モジュールは別途提供が必要。
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を想定しているため、将来の API 変更は影響を受ける可能性あり。
- 一部のモジュール（strategy / execution / monitoring）はパッケージ公開に含まれるが、今回のソース提供内では実装ファイルが省略されている（別途実装を想定）。

Security
- 特別なセキュリティ修正は今回の初回リリースには含まれない。APIキー等の取り扱いは環境変数を経由する想定。

References
- 本 CHANGELOG はソースコード内のドキュメント文字列・コメントと実装から推測して作成しています。実際の運用/設計意図と差異がある場合があります。