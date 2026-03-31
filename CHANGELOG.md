# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、SemVer に基づき管理します。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-31

初回リリース — 日本株自動売買システム「KabuSys」のコア機能を実装しました。主要なサブシステム（設定管理・データETL・マーケットカレンダー・リサーチ・AIによるニュース解析・レジーム判定）を提供します。

### 追加 (Added)

- パッケージ初期化
  - src/kabusys/__init__.py: パッケージエントリポイント（version=0.1.0）。公開サブパッケージを __all__ で定義。

- 設定 / 環境変数管理
  - src/kabusys/config.py:
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - export KEY=val 形式やシングル/ダブルクォート、エスケープ、コメント取り扱い等に対応した堅牢な .env パーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスを通じた型付き設定アクセス（J-Quants / kabu API / Slack / DB パス / 環境切替等）。
    - 設定値の検証（KABUSYS_ENV、LOG_LEVEL 等の有効値チェック）、必須環境変数取得時のエラー報告。

- AI モジュール（ニュースNLP / 市場レジーム判定）
  - src/kabusys/ai/news_nlp.py:
    - raw_news と news_symbols を集約して銘柄ごとにニューステキストを作成し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを生成。
    - バッチ処理（最大 20 銘柄/チャンク）、記事トリム（記事数・文字数上限）、レスポンス検証、スコアの ±1.0 クリップ。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフの実装。
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）と部分失敗時の既存データ保護。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - calc_news_window ユーティリティ（JST→UTCでウィンドウを計算）。

  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200 日移動平均乖離（比率）とニュース由来のマクロセンチメントを重み付け（70:30）して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに冪等書き込み。
    - DuckDB からの過去データ取得はルックアヘッドを防ぐため target_date 未満のみを参照。
    - OpenAI 呼び出しは独自実装（news_nlp と直接共有せずモジュール結合を低減）。
    - API エラー時は macro_sentiment=0.0 で継続するフェイルセーフ実装。
    - リトライ・バックオフ、JSON レスポンスパース保護。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M リターン、MA200乖離）、ボラティリティ（20日 ATR 等）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）計算を実装。
    - DuckDB のウィンドウ関数を活用した高速集計、データ不足時の None 扱い。
    - 外部 API に依存しない純粋計算モジュールとして設計。

  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman）計算、ランク化ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等を使わず標準ライブラリと DuckDB のみで完結する実装。

  - src/kabusys/research/__init__.py:
    - 主要関数を再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- データ / カレンダー管理と ETL
  - src/kabusys/data/calendar_management.py:
    - market_calendar を用いた営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録がない場合は曜日ベース（土日除外）でフォールバックする一貫した動作。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィルと健全性チェックを実装。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py:
    - ETLResult データクラス（ETLの取得数・保存数・品質問題・エラー等を集約）。
    - ETL パイプラインのためのユーティリティ（最終取得日の判定、テーブル存在チェック、差分取得・バックフィル方針等）。
    - 品質チェック (quality モジュール想定) と処理継続方針（Fail-Fast ではなく問題収集）。

  - src/kabusys/data/__init__.py:
    - ETLResult の公開インターフェースを再エクスポート。

### 変更 (Changed)

- 設計上の重要な方針を明文化（コード内ドキュメンテーションとして実装）
  - 全 AI/解析処理は datetime.today()/date.today() を直接参照せず、必ず呼び出し側から target_date を受け取る設計（ルックアヘッドバイアス防止）。
  - OpenAI 等外部 API 呼び出しは失敗時に例外で停止させず、フェイルセーフ（ゼロスコアやスキップ）で処理継続する方針。
  - DuckDB との互換性考慮（executemany に空リストを渡さない等のワークアラウンド）。

### 修正 (Fixed)

- （明示的なバグ修正履歴はなし。初回実装で多数のフェイルセーフとログ出力を実装し、運用上の問題を軽減しています。）

### 注意事項 / マイグレーション (Notes)

- OpenAI API
  - news_nlp/regime_detector は OpenAI の JSON Mode（response_format）を利用します。動作には OPENAI_API_KEY の設定が必要です。未設定の場合は ValueError を送出します。
  - API で 5xx やネットワークエラーが発生した場合は自動リトライ（指数バックオフ）を行い、最終的に失敗した場合は対象部分をスキップして0.0や空辞書で継続します。

- .env の自動読み込み
  - プロジェクトルートは本ファイル位置から上位ディレクトリで .git または pyproject.toml を探して判定します。パッケージ配布後も適切に動作することを意識しています。
  - OS 環境変数は保護され、.env.local は優先的に上書きされます。

- DuckDB
  - 一部クエリは DuckDB の挙動（リストバインド, executemany 挙動）を考慮して実装されています。運用環境の DuckDB バージョン差による注意が必要です。

### 既知の制約 (Known Limitations)

- 現バージョンでは PBR や配当利回りなど一部バリューメトリクスは未実装。
- news_nlp のレスポンス検証は堅牢に行っていますが、LLM の自由な出力に完全に依存するため予期しない形式が帰った場合はスキップされます。
- calendar_update_job は J-Quants クライアント実装（kabusys.data.jquants_client）が正しく提供されることを前提とします。

---

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノート作成時は変更差分 / リリース担当者の確認を行ってください。）