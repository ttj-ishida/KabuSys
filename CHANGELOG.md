# Changelog

すべての注記は「Keep a Changelog」の形式に従い、重要な変更点を日付付きで記載しています。

※このCHANGELOGはソースコードからの推測に基づき作成しています。

## [Unreleased]

### Added
- （未リリース）将来に向けた小さな改善やドキュメント補強を想定。

---

## [0.1.0] - 2026-04-03

初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装しました。主な追加点は次の通りです。

### Added
- パッケージ構成
  - 基本パッケージ `kabusys` を追加。サブモジュールは data, research, ai, execution, monitoring, strategy 等を想定して公開（__all__ に data, strategy, execution, monitoring を設定）。
  - パッケージバージョン管理（__version__ = "0.1.0"）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイル と環境変数の自動読み込み機能を実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数による自動ロード無効化をサポート。
  - .env パーサーは以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - コメント扱いの判定（クォート外での # 等）
  - _load_env_file で "protected"（OS 環境変数）セットを用いて上書き制御。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能：
    - J-Quants / kabuステーション API、LINE Messaging、DB パス（duckdb/sqlite）、監視関連 (pid/kill flag)、閾値、環境モード（development/paper_trading/live）とログレベル検証など。
    - 必須環境変数未設定時は明確な ValueError を送出。

- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を利用し、指定タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST 相当）内のニュースを銘柄毎に集約して OpenAI (gpt-4o-mini) に JSON Mode で送信しセンチメント（-1.0〜1.0）を算出。
    - API 呼び出しはバッチ（最大 20 銘柄/回）で行い、429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ。
    - レスポンスを厳密にバリデートし、スコアを ±1.0 にクリップ。部分失敗でも他銘柄の既存スコアを保護するため DELETE→INSERT を銘柄絞り込みで実行（冪等性を重視）。
    - JSON パースに失敗した場合はログ出力して対象をスキップ（例外を投げずフェイルセーフ）。
    - テスト容易性のため OpenAI 呼び出し点を _call_openai_api で抽象化しパッチ可能。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロニュースはキーワードでフィルタ（複数キーワード）、LLM は gpt-4o-mini を使用。API 失敗時は macro_sentiment=0.0 として継続。
    - MA 計算ではルックアヘッドバイアスを防ぐため target_date 未満のデータのみ使用。データ不足時は中立（1.0）にフォールバック。
    - OpenAI 呼び出しのリトライ/エラーハンドリングを実装。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar）を実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar 未取得時は曜日ベース（土日非営業）でフォールバックする挙動を採用し、DB 登録ありの場合は DB 値を優先。
    - 夜間バッチ calendar_update_job を実装し J-Quants API から差分取得→保存（J-Quants クライアント経由）する機能を追加。バックフィルと健全性チェックを実装。
  - pipeline（ETL）
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を再エクスポート）。
    - ETL の差分取得・保存・品質チェックを想定した骨組みを実装（jquants_client 経由で保存、quality モジュールでチェック）。
    - 部分的な失敗に備えたエラ収集設計（Fail-Fast ではなく全件収集）を反映。
  - etl モジュール経由の型再エクスポート（ETLResult）。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）などの計算関数を実装: calc_momentum, calc_volatility, calc_value。
    - DuckDB 内部 SQL を活用し、prices_daily / raw_financials を参照する形で高速に計算。欠損やデータ不足に対する None フォールバックを実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算（Spearman ランク相関）、ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - pandas 等外部依存を避け、標準ライブラリと DuckDB のみで実装。rank は同順位を平均ランクで処理。
  - research パッケージに主要関数を再エクスポートして使いやすく提供。

### Changed
- （初版）コードベースの初期実装につき、互換性破壊の変更はなし。

### Fixed
- （該当なし）初回リリースのためバグ修正履歴はなし（実装には堅牢性を意識したログ・フォールバック・トランザクション処理を組み込んでいます）。

### Security
- OpenAI API キーは引数注入または環境変数（OPENAI_API_KEY）で解決。未設定時は ValueError を発生させ、誤った公開を防止。

---

開発上の設計方針（全体）
- ルックアヘッドバイアス防止: 日付参照で datetime.today()/date.today() を直接使わず、関数呼び出し側から target_date を受け取る設計。
- DuckDB を主要な分析 DB として利用。SQL と Python を組み合わせて計算を行う。
- 外部 API 呼び出しは失敗に強く、ログ出力・リトライ・フェイルセーフ（スコア 0.0 や処理スキップ）で全体処理が止まらないように設計。
- DB 書き込みは冪等性を重視（DELETE→INSERT のパターンや ON CONFLICT を想定）し、部分失敗が他データを毀損しないよう配慮。
- テスト容易性のため OpenAI 呼び出し点など外部依存箇所はモック差し替えしやすい構造にしている。

もしこのCHANGELOGに追加してほしい詳細（例えば各関数の既知の制約、想定するマイグレーション手順、既知の未実装項目など）があればお知らせください。