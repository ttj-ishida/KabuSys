CHANGELOG
=========

すべての変更は「Keep a Changelog」の形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （現在の開発中の変更はここに列挙してください）

0.1.0 - 2026-03-29
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報:
    - src/kabusys/__init__.py によるバージョン定義: __version__ = "0.1.0"
    - __all__ による主要サブパッケージ公開: data, strategy, execution, monitoring

- 環境変数・設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml から検出（CWD 非依存）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能
  - .env ファイル行パーサの実装
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いを考慮
  - Settings クラスの提供（環境変数取得ラッパ）
    - J-Quants, kabuステーション, Slack, データベースパスなどのプロパティを用意
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）
    - duckdb/sqlite のデフォルトパス設定

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを取得
  - 処理特徴:
    - JST 基準のタイムウィンドウ計算（calc_news_window）
    - 1銘柄あたり最大記事数・最大文字数によるトークン肥大対策
    - 最大 20 銘柄単位のバッチ送信（_BATCH_SIZE）
    - JSON Mode を利用した厳密な JSON 出力期待・レスポンスバリデーション
    - 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーに対する指数バックオフリトライ
    - スコアを ±1.0 にクリップ
    - スコア書き込みは部分失敗時に既存データを消さないようにコード列で絞った DELETE → INSERT を実行（トランザクション）
  - テストフック: _call_openai_api を unittest.mock.patch で差し替え可能

- マーケット・レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime を算出・保存
  - 処理特徴:
    - DuckDB からの過去データ参照は target_date 未満に制限してルックアヘッドを排除
    - マクロ記事が無い場合や API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）
    - OpenAI 呼び出しは専用関数を使用しモジュール間結合を避ける
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と失敗時の ROLLBACK ハンドリング
    - デフォルトモデル gpt-4o-mini、リトライ構成（最大3回、指数バックオフ）

- 研究用ファクター計算群（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率（ma200_dev）
    - calc_volatility: 20日 ATR、ATR比率、20日平均売買代金、出来高比率等
    - calc_value: raw_financials からの EPS/ROE を用いた PER / ROE の算出（target_date 以前の最新財務データ取得）
    - 各関数は DuckDB（prices_daily / raw_financials）を参照し、データ不足時は None を返す設計
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括 SQL で取得
    - calc_ic: スピアマンランク相関（IC）の計算（欠損・同値処理、最小レコード数チェック）
    - rank: 同順位は平均ランクで処理（丸めで ties 検出漏れ回避）
    - factor_summary: count/mean/std/min/max/median の集計

- データ関連ユーティリティ（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを提供
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装
    - DB にデータが無い場合は曜日ベースのフォールバック（週末を非営業日）を採用
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新、バックフィルと健全性チェックを実装
  - pipeline:
    - ETLResult データクラスを導入（ETL 実行の各種メトリクス・品質問題・エラーを保持）
    - 差分取得・保存・品質チェックの設計方針を実装（jquants_client / quality を利用）
  - etl モジュールは pipeline.ETLResult を再エクスポート

- パッケージ公開 API の整理
  - ai/__init__ で score_news を公開
  - research/__init__ で主要関数を再公開

Design / Reliability Notes
- ルックアヘッドバイアス回避:
  - 各種処理は内部で datetime.today() / date.today() を直接参照せず、必ず引数の target_date に基づいて処理します。
- フェイルセーフ設計:
  - OpenAI API の失敗は多くのケースでスキップやデフォルト値（0.0）にフォールバックし、例外で全体処理を停止しない設計です（ただし API キー未設定は ValueError を送出）。
- DuckDB トランザクション:
  - 書き込みは明示的なトランザクション (BEGIN / COMMIT / ROLLBACK) で行い、ROLLBACK の失敗は警告ログで記録します。
- テスト容易性:
  - OpenAI 呼び出し箇所（_call_openai_api）を差し替え可能にしてユニットテストが容易になるよう設計。

Important (互換性 / 注意点)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings プロパティで必須とされており未設定時は ValueError になります（実行経路により必須のものが異なります）。
  - OpenAI を使用する関数（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY のいずれかを必須とします。空文字列も未設定扱いです。
- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ依存:
  - 多くの関数は特定テーブル（例: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar）を前提として動作します。実行前に必要なスキーマ／カラムが存在することを確認してください。
- OpenAI のレスポンス形式:
  - JSON Mode（厳密な JSON）の出力を期待していますが、安全策として前後のテキスト抜き出しやパース失敗時のフォールバックを実装しています。

Changed
- 初リリースのため該当なし

Fixed
- 初リリースのため該当なし

Removed
- 初リリースのため該当なし

Deprecated
- 初リリースのため該当なし

Security
- 初リリースのため該当なし

Contributors
- （ソースコードからは作者情報を取得できません。実際のプロジェクトでは CONTRIBUTORS や Git の履歴に記載してください。）