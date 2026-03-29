CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- セキュリティ (Security)

Unreleased
----------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

Added
-----
- 初回公開リリース。
- パッケージのメタ情報を追加
  - kabusys.__version__ を "0.1.0" に設定し、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の堅牢なパース実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント対応。
    - 無効行やコメント行のスキップ。
  - OS 環境変数を保護する protected 機構（.env の上書きを制御）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別（development / paper_trading / live）/ログレベル等の取得をサポート。
  - 必須環境変数未設定時は明確な ValueError を送出。

- AI ニュース解析（kabusys.ai.news_nlp）
  - ニュース記事を OpenAI（gpt-4o-mini）でバッチセンチメント評価し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む機能を実装。
  - 対象取得ウィンドウ（JST 前日 15:00 〜 当日 08:30）を calc_news_window で計算。
  - 銘柄ごとに最新記事を集約（記事数・文字数制限）し、最大 _BATCH_SIZE 銘柄ずつ API に送信するチャンク処理を実装。
  - JSON Mode による応答のバリデーション実装（レスポンスパース復元処理含む）。
  - API 一時エラー（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフによるリトライ。
  - 取得スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に（DELETE → INSERT）保存。
  - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。

- AI マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
  - ma200_ratio 計算、マクロキーワードに基づく raw_news 抽出、LLM 呼び出し（gpt-4o-mini）で macro_sentiment を算出。
  - API 失敗時は macro_sentiment = 0.0 とするフェイルセーフ。
  - レジームスコアを market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。エラー時は ROLLBACK を試行して上位へ例外伝播。
  - テスト用に _call_openai_api を差し替え可能。

- 研究（research）モジュール（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離率（データ不足時は None）。
    - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から取得）。
    - Volatility: 20日 ATR（true range の NULL 伝播を正しく扱う）、20日平均売買代金、出来高比率。
  - feature_exploration: calc_forward_returns（任意ホライズンの将来リターンを一度のクエリで取得）、calc_ic（スピアマンのランク相関 = IC）、factor_summary（count/mean/std/min/max/median）、rank（平均ランク処理）。
  - DuckDB の SQL ウィンドウ関数を活用し、外部 API に依存しない純粋なデータ処理実装。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar ベースの営業日判定、次・前営業日取得、期間内の営業日列挙、SQ 日判定を提供。
    - market_calendar 未取得時の曜日ベースフォールバック（週末を非営業日）を一貫して採用。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック・保存処理。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー収集などを集約）。
    - 差分更新ロジック、バックフィル方針、品質チェックの扱い方針（重大度の扱い）を実装。
    - DuckDB テーブル存在チェックや max date 抽出等のユーティリティを実装。
  - ETLResult を kabusys.data.etl 経由で再エクスポート。

- DuckDB を前提とした堅牢な DB 操作
  - executemany の空リストバインドに関する互換性対策（DuckDB 0.10 を想定）。
  - SQL 内での ROW_NUMBER / LEAD / LAG / ウィンドウ関数多用により効率的に集計。

Changed
-------
- （初版のため該当なし）

Fixed
-----
- （初版のため該当なし）

Deprecated
----------
- （初版のため該当なし）

Security
--------
- OpenAI の API キー未設定時は明確に ValueError を送出して操作ミスを検出。
- 環境変数自動ロード時に OS 環境変数を保護（上書き防止）する仕組みを実装。

Notes / Known dependencies and requirements
------------------------------------------
- OpenAI SDK を利用（OpenAI API キーが必要）。AI 機能 (news_nlp, regime_detector) を実行するには環境変数 OPENAI_API_KEY または api_key 引数が必須。
- J-Quants クライアント（kabusys.data.jquants_client）を想定しているが、この差分は本リポジトリ内に実装済みか外部依存か確認する必要あり。
- DuckDB 接続オブジェクト（DuckDBPyConnection）を引数に取る関数が多いため、動作には DuckDB が必要。
- DuckDB のバージョンによって executemany の扱いなど微妙な挙動差異が存在する旨を考慮（実装内で回避策を採用）。

テストフレンドリーな設計メモ
--------------------------
- OpenAI 呼び出しを行う内部関数（各モジュールの _call_openai_api）を unittest.mock.patch で置換可能にしており、外部APIへの依存を抑えてユニットテストを容易にしています。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効にでき、CI/テスト環境での副作用を制御できます。

今後の改善案（草案）
--------------------
- news_nlp のレスポンス検証をより厳密にする（スキーマ検証やサンプルベースの QA）。
- ETL の増分単位や並列化オプションの追加。
- AI モジュールのモデル切替やコスト制御の抽象化（model name を外部設定化）。
- jquants_client のモック実装やテスト用フィクスチャを提供。

----------------------------------------
本CHANGELOGはコードベースの内容から推測して作成しています。実際のリリース手順や日付は適宜調整してください。