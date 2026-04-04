# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初回公開リリースを記載しています。

全般な方針：
- 日付や DB クエリにおけるルックアヘッドバイアス防止（datetime.today()/date.today() を直接参照しない設計）
- DuckDB 互換性や部分失敗に対する保護（idempotent 書き込み、executemany の空パラメータ回避など）
- 外部 API 呼び出し（OpenAI / J-Quants）についてはリトライ・フォールバックを設計に組み込み、テスト容易性のため一部呼び出しを差し替え可能に実装

[0.1.0] - 2026-04-04
====================

Added
-----
- パッケージ初期リリース
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"、公開 API (__all__) を設定。

- 環境・設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定をロードする自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行い、配布後やカレントディレクトリに依存しない実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装:
    - export KEY=val 形式に対応、シングル/ダブルクォート内のエスケープ、行末コメントの取り扱いなどを考慮した堅牢なパース。
  - _load_env_file にて既存 OS 環境変数を保護する protected キーセットをサポート。
  - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別・ログレベル検証などをプロパティ経由で取得できるように実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証（有効な値以外は ValueError）。
    - ファイルパスは Path に展開（expanduser 対応）。
    - 監視用フラグや閾値のデフォルト値を定義（CPU/MEM/DISK しきい値等）。

- AI (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価して ai_scores テーブルへ書き込む処理を実装。
    - 時間ウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 に対応、calc_news_window を提供）。
    - バッチ処理: 1 コールあたり最大 20 銘柄、1 銘柄あたり最大 10 件・3000 文字にトリム。
    - レスポンス検証ロジック: JSON パース、"results" 配列の存在、コード一致、数値検証、スコアクリップ(±1.0)。
    - リトライ/バックオフ: 429/ネットワーク/タイムアウト/5xx を想定した指数バックオフ、最大リトライ回数の制御。
    - DuckDB への書き込みは部分失敗時の保護を考慮（該当コードのみ DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し部を差し替え可能（_call_openai_api を patch 可能）。
  - マーケットレジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - MA200 比率計算（target_date 未満のデータのみ使用、データ不足は中立扱い）。
    - マクロニュース抽出（news_nlp.calc_news_window を使用）と OpenAI 呼び出しによる macro_sentiment 評価。記事が無い場合は LLM 呼び出しをスキップし 0.0 を使用。
    - レジームスコア合成と閾値によるラベル化、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API 失敗やレスポンスパース失敗時は安全側フォールバック（macro_sentiment=0.0）で運用継続。

- Data / ETL / カレンダー (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを参照/更新するユーティリティ群を追加。
    - 営業日判定（is_trading_day）、翌/前営業日取得（next_trading_day / prev_trading_day）、期間内の営業日列挙（get_trading_days）、SQ 判定（is_sq_day）を実装。
    - DB の登録があれば DB 値を優先、未登録日は曜日（平日）ベースでフォールバックする一貫した挙動を実装。
    - calendar_update_job を追加し、J-Quants API から差分取得して market_calendar テーブルを冪等に更新（バックフィル / 健全性チェック含む）。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを実装し、ETL 実行の集計結果（取得数・保存数・品質問題・エラー）を返却・ログ用辞書化できるようにした。
    - 差分更新、保存（jquants_client の save_* 関数利用）、品質チェック（quality モジュール連携）の設計方針をコメントで明確化。
    - duckdb テーブル存在チェックや最大日付取得ユーティリティを実装。
    - デフォルトのバックフィル日数やカレンダー先読み日数を定義。
    - kabusys.data.etl で ETLResult を再エクスポート。

- Research (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算する calc_momentum を実装。データ不足時は None を返す。
    - Volatility / Liquidity: 20日 ATR、ATR_pct、20日平均売買代金、出来高比率を計算する calc_volatility を実装。TR の NULL 伝播を考慮。
    - Value: raw_financials から最新財務データを取得して PER / ROE を算出する calc_value を実装（EPS が 0 または欠損時は None）。
    - 実装は DuckDB 上の SQL と Python により完結し、本番発注 API 等にアクセスしない設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算 calc_forward_returns（任意の horizon リスト対応、horizons のバリデーションあり）。
    - IC（Spearman の ρ）計算 calc_ic（欠損や ties に対する処理、3 サンプル未満では None）。
    - ランキングユーティリティ rank（同順位は平均ランクを返す、浮動小数の丸めで ties 検出の安定化）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median を算出）。
  - 既存ユーティリティの再エクスポート:
    - kabusys.research.__init__ で zscore_normalize（kabusys.data.stats）等を再エクスポート。

Changed
-------
- （初版のため特記事項なし）

Fixed
-----
- （初版のため特記事項なし）

Deprecated
----------
- （初版のため特記事項なし）

Removed
-------
- （初版のため特記事項なし）

Security
--------
- OpenAI API キー未設定時は ValueError を送出して誤操作を防止する仕組みを導入（score_news / score_regime）。  
- 環境変数の自動ロード時には既存 OS 環境変数を protected として上書きから保護。

Notes / 期待される DB スキーマと前提
-----------------------------------
- 本リリースは以下のテーブルが DuckDB に存在することを前提にしています:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など
- J-Quants / kabu API クライアントモジュール（kabusys.data.jquants_client 等）に依存する箇所があるため、実行にはそれらの設定・API キーが必要です。
- OpenAI を利用する機能は環境変数 OPENAI_API_KEY または各関数の api_key 引数でキーを渡す必要があります。
- テスト時には各モジュールの _call_openai_api 等をパッチして外部 API 呼び出しをモックすることを想定しています。

今後の予定（例）
----------------
- 監視・実行関連のモジュール（execution / monitoring）に関する実装拡張
- 追加の品質チェックルールや ETL ジョブの細分化
- 運用向けの CLI / サービス化ドキュメント整備

---
以上。リリースに関する不明点や、CHANGELOG の項目追加・詳細化希望があればお知らせください。