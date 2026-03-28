# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

## [Unreleased]
- 特になし

## [0.1.0] - 2026-03-28
初回リリース。本リポジトリは日本株の自動売買／データ基盤／リサーチ用ユーティリティ群を提供します。主な追加点と設計方針は以下の通りです。

### 追加（Added）
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - モジュール公開: data, research, ai, その他基盤モジュールをエクスポート。

- 環境設定（kabusys.config）
  - .env / .env.local を自動読み込み（読み込み順: OS環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化。
  - .git または pyproject.toml を手掛かりにプロジェクトルートを検出する実装（CWD非依存）。
  - .env の行パーサを実装（export 構文、シングル/ダブルクォート、インラインコメント等に対応）。
  - settings クラスを提供し、必須環境変数の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
  - 環境値検証: KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）の検証とヘルパー属性（is_live, is_paper, is_dev）。
  - デフォルト DB パス: DuckDB/SQLite のパスを設定可能。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理 API（J-Quants クライアント経由）との連携、market_calendar テーブルの夜間バッチ更新（calendar_update_job）。
    - 営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データが不完全な場合は曜日ベースのフォールバックを使用。
    - バックフィル、先読み、健全性チェック（将来日付の異常検出）を実装。
  - pipeline / ETL:
    - ETLResult データクラスによる詳細な実行結果管理（取得数・保存数・品質問題・エラー一覧）。
    - 差分更新・バックフィル・品質チェックを含む ETL パイプライン設計（jquants_client と quality モジュール連携を想定）。
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティ。
  - etl モジュールから ETLResult を再エクスポート。

- 研究（kabusys.research）
  - factor_research:
    - モメンタム、ボラティリティ（ATR）、バリュー（PER, ROE）等のファクター計算関数: calc_momentum, calc_volatility, calc_value。
    - DuckDB 上の SQL とウィンドウ関数を活用して日付基準で計算。データ不足時の None 戻しやログ出力を実装。
  - feature_exploration:
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - 情報係数（IC）計算: calc_ic（スピアマンランク相関）、rank（同順位は平均ランク）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
  - zscore_normalize は data.stats からの再利用を想定して公開。

- AI / ニュース処理（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントを算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたりの記事トリム（最大記事数・最大文字数）によりトークン肥大化を抑制。
    - レスポンスのバリデーションと数値型への正規化、スコアの ±1.0 クリッピング。
    - リトライ／エクスポネンシャルバックオフ（429/ネットワーク断/タイムアウト/5xx）とフェイルセーフ（失敗時は該当チャンクをスキップ）。
    - ai_scores テーブルへの冪等書き込み（該当コードのみ DELETE → INSERT）。
    - calc_news_window: JST基準のニュース集計ウィンドウ（前日15:00〜当日08:30 JST を UTC に変換）を提供。
  - regime_detector:
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）と、news_nlp ベースのマクロセンチメント（重み 30%）を合成し市場レジーム（bull/neutral/bear）を日次で判定。
    - OpenAI 呼び出しは独立実装（モジュール結合を避ける）で、API 失敗時は macro_sentiment=0.0 にフォールバック。
    - DuckDB を用いたデータ取得と冪等な market_regime テーブル書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - AI 関連実装は gpt-4o-mini を使用し、テスト用に _call_openai_api をモック可能。

### 変更（Changed）
- 初回公開のため該当なし。

### 修正（Fixed）
- 初回公開のため該当なし。

### セキュリティ（Security）
- API キーや必須設定は Settings 経由で必ず取得する設計（未設定時は ValueError を送出）。
- .env ファイル読み込みで OS 環境変数を保護する protected オプションを実装。

### 実装上の設計方針・制約（Notes / Known limitations）
- ルックアヘッドバイアス回避のため、datetime.today() / date.today() を関数内部で直接参照せず、外部から target_date を注入する設計の関数が多い。
- DuckDB（ローカル解析用）を前提に実装しており、DuckDB のバージョン差異に配慮した実装（executemany の空リスト回避など）を行っている。
- OpenAI 呼び出しは JSON Mode を期待するが、レスポンスに雑多な前後テキストが混入するケースを復元するロジックを入れている。
- 部分失敗時に既存データを保護するため、DB 書き込みは対象コードを限定して DELETE → INSERT を行うアプローチを採用している。
- jquants_client / quality 等の外部モジュールは想定されるインターフェースに依存（実装は別モジュール）。

### 互換性（Backward compatibility）
- 初回リリースのため後方互換性に関する既知の問題はなし。

---

開発者向けの詳しい利用方法や API 仕様、DB スキーマ、運用手順は別途ドキュメント（README / StrategyModel.md / DataPlatform.md 等）に記載する予定です。