CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
Versions are governed by Semantic Versioning.

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-03-29
--------------------

初回リリース。日本株自動売買プラットフォームの基盤となる機能群を実装しました。
主要な追加点、設計方針、既知の前提・制約を以下にまとめます。

Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ == "0.1.0"）。
  - 公開モジュール群を __all__ で整理（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - .env ファイルパーサを実装（コメント行、export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの取扱いに対応）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 必須設定を取得する _require と Settings クラスを提供。J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを公開し、値チェック（有効な env, log level）を行う。

- AI 関連 (kabusys.ai)
  - ニュースセンチメント（score_news）
    - raw_news / news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとの sentiment を算出。
    - タイムウィンドウ: 対象日の「前日15:00 JST」〜「当日08:30 JST」を UTC に変換して利用。calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事数上限、文字数トリムなどトークン肥大対策を実装。
    - エラー対策: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、応答バリデーション（JSON 抽出、results フォーマット検証、スコアの数値検査）、スコアは ±1.0 にクリップ。
    - DB 書き込みは冪等（該当日・該当コードを DELETE → INSERT）で部分失敗時に既存データを保護。
    - テスト容易性: OpenAI 呼び出し部分をモック可能（内部の _call_openai_api を patch）。

  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次のレジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算、マクロニュース抽出（キーワードベース）、OpenAI 呼び出し、スコア合成、閾値判定、market_regime テーブルへの冪等書き込みを実装。
    - フェイルセーフ: API 呼び出し失敗時は macro_sentiment=0.0 で継続。DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で安全に処理し、例外時に ROLLBACK を試行。
    - OpenAI 呼び出しはテストで差し替え可能。API エラー・リトライロジック（再試行時のログと待機）を実装。

- データ基盤 / ETL (kabusys.data)
  - ETL の公開インターフェースとして ETLResult を導出・再エクスポート（kabusys.data.etl）。
  - ETL パイプライン (kabusys.data.pipeline)
    - 差分取得、バックフィル、品質チェック（quality モジュール経由）、保存（jquants_client の save_* を利用）という設計に基づく ETLResult データクラスを実装。
    - ETL 実行結果の集約、品質問題のシリアライズ、エラー判定ヘルパーを提供。
    - テスト・互換性を考慮したテーブル存在チェックや最終日取得ユーティリティを実装。

  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを参照した営業日判定ロジックを実装（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB にカレンダーがない場合は曜日（平日/週末）ベースのフォールバックを行い、DB 登録がある場合は DB 値優先の一貫した判定を保証。
    - カレンダー夜間更新ジョブ（calendar_update_job）を実装。J-Quants API から差分取得・保存し、バックフィルと健全性チェック（未来日の過剰な先読み防止）を行う。
    - 最大探索日数制限や NULL 値検出時のログ出力など安全策を組み込み。

- Research / ファクター計算 (kabusys.research)
  - ファクター計算関数を実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - calc_value: raw_financials からの EPS/ROE を組み合わせて PER/ROE を算出（EPS が無効な場合は None）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を利用）。
    - calc_ic: ファクタ値と将来リターンのスピアマン（ランク）相関を計算。
    - rank: 同順位は平均ランクで処理（丸めで ties 検出を安定化）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
  - zscore_normalize をデータユーティリティから再エクスポート。

- ロギング・設計方針
  - ルックアヘッドバイアスを避けるため、日付取得に datetime.today()/date.today() を直接参照しない設計を各モジュールで採用（関数引数で target_date を受け取る）。
  - DuckDB を中心に SQL ウィンドウ関数を活用し、欠損/データ不足時の挙動（None / ログ出力）を一貫して扱う。
  - OpenAI 呼び出しや外部 API 呼び出しはフェイルセーフ設計（失敗時に処理を継続、ログ出力）を優先。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- .env 読み込み時に OS 環境変数を保護する仕組み（.env の上書きを制御）を実装。
- OpenAI API キーは引数注入または OPENAI_API_KEY 環境変数経由で明示的に指定する必要がある旨を厳格化（未指定時は ValueError を送出）。

Notes / 前提・既知の制約
- 実行環境
  - DuckDB と openai（OpenAI Python SDK）が必須です。
  - コードは型アノテーションに Python 3.10+ の構文（| union、from __future__ import annotations）を想定しています。
- 必須環境変数（Settings で _require を使う項目）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を使う機能は OPENAI_API_KEY（または各関数の api_key 引数）を必要とします。
- データベーススキーマ期待値
  - モジュールは prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などのテーブル構造を前提としています（実行前にスキーマ準備が必要）。
- テスト容易性
  - OpenAI API の呼出し箇所は内部関数（_call_openai_api）を patch / モックすることでユニットテストが可能です。
- ロギング
  - 多くの関数は詳細な debug / info / warning / exception ログを出力します。運用時は Settings.log_level を設定してください。

Migration
- 初回リリースのため移行手順はありません。導入時は上記前提（環境変数、DB スキーマ、依存パッケージ）を満たしてください。

Contact / Contributing
- バグ報告・機能要望はリポジトリの Issue を利用してください。コード内にテストフレンドリーな箇所を多く設けていますので、ユニットテスト・ CI の追加歓迎します。

--- End of CHANGELOG ---