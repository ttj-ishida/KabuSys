CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記載します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

Unreleased
----------
（現在のところ未リリースの変更はありません）

0.1.0 - 2026-03-28
-----------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ公開 API: kabusys.__init__ で "data", "strategy", "execution", "monitoring" を公開。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルや環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自パッケージ位置からプロジェクトルートを探索（CWD に依存しない実装）。
  - .env パーサー改善:
    - 空行 / コメント行（先頭の #）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォート無しの値でのインラインコメント処理（直前がスペース/タブの場合のみコメントとして扱う）。
  - 自動ロード順序: OS 環境変数 > .env.local (override=True) > .env (override=False)。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - Settings クラスを提供:
    - J-Quants / kabuAPI / Slack / DB パス等のプロパティを提供。
    - 値検証: KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の妥当性検査。
    - duckdb/sqlite のデフォルトパス設定（expanduser 対応）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp):
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores テーブルに書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数・文字数制限（トリム）を実装。
    - JSON Mode を利用した厳密なレスポンス検証およびスコアクリップ（±1.0）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスのパース失敗や API エラーはフェイルセーフでスキップ（例外を上げずに継続）。
    - DuckDB への書き込みは部分失敗時の保護を考慮して、該当コードのみ DELETE → INSERT で置換（冪等性・部分失敗耐性）。
    - テスト容易性のため OpenAI 呼び出しラッパー（_call_openai_api）を patch 可能に設計。

  - 市場レジーム判定 (kabusys.ai.regime_detector):
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、market_regime テーブルへ冪等書き込み。
    - マクロニュースはキーワードフィルタリング（日本語・英語のマクロキーワードセット）で抽出。
    - OpenAI 呼び出しのリトライ（429/ネットワーク/タイムアウト/5xx）・冪等書き込み・フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームは閾値で 'bull' / 'neutral' / 'bear' を判定。
    - lookahead バイアス対策（target_date 未満のみのデータ使用、datetime.today() を参照しない）。

- データ処理関連 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management):
    - market_calendar を利用した営業日判定 API を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未登録日のフォールバックは曜日ベース（土日除外）。
    - 夜間バッチ更新 calendar_update_job により J-Quants から差分取得・冪等保存（backfill / sanity check を含む）。
    - 最大探索日数 _MAX_SEARCH_DAYS やバックフィル/先読みの定義を導入し無限ループや異常データを防止。

  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl):
    - ETLResult データクラスを導入し ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化。
    - _get_max_date 等のユーティリティ、差分取得・backfill・品質チェックの設計方針を実装（jquants_client との連携想定）。
    - kabusys.data.etl は ETLResult を再エクスポート。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER, ROE を算出（EPS 0/NULL の場合は None）。
    - 各関数は prices_daily / raw_financials のみ参照し、本番取引には影響しない設計。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズンの将来リターンを一括取得（複数ホライズン対応・入力検証あり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を算出（有効レコードが 3 件未満なら None）。
    - rank(values): 同順位は平均ランクを返す実装（浮動小数点丸め誤差対策）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
    - zscore_normalize は kabusys.data.stats から再エクスポート。

Design / Implementation Notes
- DuckDB を主要なデータストアとして想定（DuckDBPyConnection を引数に取る設計）。
- ルックアヘッドバイアス防止のため、全 AI / リサーチモジュールは内部で datetime.today()/date.today() を直接参照しない。target_date を外部から注入して運用・テストを容易に。
- DB 書き込みは冪等性を重視（BEGIN / DELETE / INSERT / COMMIT と ROLLBACK 保護）。
- OpenAI API 呼び出しは JSON Mode を利用し、厳格なレスポンス検証を行う。テスト時に差し替え可能な内部ラッパーを提供。
- API リトライは 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフを実装。非再試行系エラーはログ記録して安全にスキップする方針。
- 研究モジュールは外部依存（pandas 等）を持たない純標準ライブラリ実装を目指す。

Security / Requirements
- OpenAI API キー（OPENAI_API_KEY）や J-Quants / Slack 関連の必須環境変数が未設定の場合、一部関数は ValueError を送出する（使用前に .env を用意することを推奨）。
- Slack / Kabu API 等の機密情報は環境変数経由で設定する設計。

Known limitations / TODO
- 現バージョンでは PBR / 配当利回り等のバリュー指標は未実装（calc_value で注記）。
- news_nlp/regime_detector の OpenAI モデルは gpt-4o-mini を想定。将来的なモデル変更時はレスポンス検証の更新が必要。 
- monitoring / execution / strategy の具体実装（本番発注・監視ロジック）はパッケージ API に含まれているが、本リリースにおいては詳細実装がない／別ファイルでの拡張を想定。

Breaking Changes
- 初回リリースのため破壊的変更はありません。

Acknowledgements
- 本リリースはローカル DuckDB + J-Quants / OpenAI 連携を想定した日本株向け自動売買・研究基盤のプロトタイプ実装を目指しています。

---  
（以降のリリースでは機能追加・バグ修正・破壊的変更を同フォーマットで追記してください）