CHANGELOG
=========

All notable changes to this project will be documented in this file.
このファイルは Keep a Changelog の形式に従って作成されています。
（https://keepachangelog.com/ja/1.0.0/）

Unreleased
----------

- （なし）

0.1.0 - 2026-03-31
------------------

初期リリース。プロジェクトのコア機能を実装しました。以下の主要コンポーネントと機能を含みます。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = "0.1.0"）。
  - __all__ に data, strategy, execution, monitoring を公開（将来のモジュール配置を想定）。

- 設定/環境変数管理（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロードする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを提供し、アプリ全体の設定アクセスを集中管理（J-Quants トークン、kabu API 設定、Slack、DB パス、監視閾値、環境/ログレベル判定など）。
  - 環境変数未設定時は明確なエラーを投げる _require 関数を用意。

- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp モジュール（score_news）
    - raw_news と news_symbols を集約し、銘柄別にニュースをまとめて OpenAI（gpt-4o-mini）へ送信してセンチメントを算出。
    - バッチ処理（最大20銘柄/チャンク）、トークン膨張対策（記事数・文字数トリム）、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - 429・ネットワーク切断・タイムアウト・5xx に対する指数バックオフとリトライを実装。その他のエラーはスキップして継続（フェイルセーフ）。
    - calc_news_window を提供（JST 基準のニュース収集ウィンドウ計算。ルックアヘッドバイアスを避ける設計）。
    - テストフックとして OpenAI 呼び出し部分を置き換え可能に設計（unittest.mock.patch を想定）。

  - regime_detector モジュール（score_regime）
    - 日次の市場レジーム判定を実装。ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して regime_score を算出。
    - LLM 呼び出しは独立実装でモジュール間の結合を避け、API エラー時は macro_sentiment を 0.0 として継続するフェイルセーフ設計。
    - レジーム結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - OpenAI クライアント生成時に api_key 注入可能（テスト容易性を考慮）。

- データ基盤（kabusys.data）
  - calendar_management
    - JPX カレンダーの管理ロジックを実装（market_calendar を参照）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（土日）でフォールバック。DB 登録値が優先される一貫した判定ロジック。
    - calendar_update_job を実装（J-Quants API から差分取得して冪等保存、バックフィルと健全性チェックを含む）。
  - pipeline（ETL）
    - ETLResult データクラスを追加（ETL 実行結果の構造化、品質問題/エラーの集約、便利な to_dict メソッド）。
    - ETL モジュール設計（差分取得、idempotent 保存、品質チェックの収集型アプローチ、テストしやすい id_token 注入）。
  - etl.py は pipeline.ETLResult を再エクスポート。

- リサーチ/ファクター（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）等の計算関数を実装。
    - DuckDB 上の prices_daily / raw_financials を参照し、(date, code) ベースの dict リストを返す設計。
    - データ不足時の None ハンドリング、ログ出力を実装。
  - feature_exploration
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ランク相関）計算、rank（同順位は平均ランク）および factor_summary（基本統計量）を実装。
    - 外部依存を持たず標準ライブラリと DuckDB だけで完結する実装。
  - research パッケージは上記関数群と zscore_normalize（data.stats から）を公開。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- OpenAI API キー等の秘匿情報は環境変数経由で取得する設計。Settings._require による未設定時の早期検出。

Notes / Implementation decisions（設計上の留意点）
- ルックアヘッドバイアス防止
  - news_nlp/regime_detector 等は datetime.today()/date.today() を内部参照せず、必ず呼び出し側から target_date を与える設計。
  - DB クエリは date < target_date や半開区間を用いる等、ルックアヘッドを避けるよう配慮。

- フェイルセーフ / 部分失敗に強い設計
  - LLM 呼び出し失敗時に全体を止めない（0.0 やスキップ）で続行することで部分的なデータ欠損に耐える。
  - ai_scores 等の DB 書き込みは対象コードのみを絞って DELETE→INSERT することで部分失敗時に既存データを保護。

- テスト容易性
  - OpenAI 呼び出しのラッパー関数をモジュール内で切り替え可能にしてモック差し替えを想定。
  - api_key を引数で注入できる関数を提供。

- DuckDB 互換性への配慮
  - executemany に空リストを渡さないチェックや、配列バインドの回避等で DuckDB バージョン差異に対応。

Known limitations / Requirements
- OpenAI API（gpt-4o-mini）および J-Quants API クライアント（kabusys.data.jquants_client）は外部サービスであり、実行には有効な API キーが必要。
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必要とします。未設定時は ValueError を送出します。
- jquants_client の実装（fetch/save 関数）は本 CHANGELOG の対象外（別モジュール参照）。
- strategy / execution / monitoring の詳細な実装は今リリースファイルに含まれていません（将来追加予定）。

Contributing
- バグ報告や改善提案は Issue を立ててください。プルリクエストはテストケースと説明を添えて送ってください。

License
- （リポジトリの LICENSE ファイルに従うこと）

--- 

（注）本 CHANGELOG は提示されたソースコードから推測して作成した初期リリースの要約です。実際の公開リリースノートとして使用する場合は、バージョン管理履歴やリリース日付、外部依存に関する正確な情報をプロジェクト実態に合わせて調整してください。