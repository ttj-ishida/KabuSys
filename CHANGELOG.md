# Changelog

すべての重要な変更点を保持するため、Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリ内のコードから推測して作成しています（実装上の意図や設計方針も併記しています）。

リンクや既知の問題は将来的に追記してください。

## [Unreleased]
- ドキュメントやマイナー改善、テストの追加予定。
- バージョン管理／リリース前にセキュリティチェックや型チェックを強化予定。

## [0.1.0] - 2026-03-27
初期リリース。以下の主要機能・設計方針を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成（src/kabusys/__init__.py）。
  - 公開モジュール群: data, research, ai, execution, strategy, monitoring（__all__ に準備）。

- 環境設定管理
  - settings クラスを提供（src/kabusys/config.py）。
    - 必須変数取得用の _require、環境の検証（KABUSYS_ENV, LOG_LEVEL）を実装。
    - DuckDB/SQLite のデフォルトパスを設定するプロパティ（duckdb_path, sqlite_path）。
  - .env ファイルの自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml 基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env と .env.local の優先度制御（OS 環境変数を保護する protected 機能）。
  - .env の柔軟なパーサ実装:
    - export KEY=val 形式、シングル/ダブルクォート内のエスケープ処理、行末コメント処理に対応。

- データプラットフォーム（Data）
  - ETL パイプラインのインターフェース（ETLResult データクラス、src/kabusys/data/pipeline.py）。
    - ETL 結果のサマリ、品質チェック結果・エラー一覧を保持する構造。
  - ETL 収集・差分更新の設計（差分取得、バックフィル、品質チェックの方針）。
  - market_calendar を管理するカレンダーモジュール（src/kabusys/data/calendar_management.py）。
    - 営業日判定 (is_trading_day)、次/前営業日取得 (next_trading_day / prev_trading_day)、期間内営業日列挙 (get_trading_days)、SQ 日判定 (is_sq_day) を提供。
    - J-Quants からの差分取得を行う夜間バッチ job (calendar_update_job) と保存ロジック。
    - market_calendar 未登録時の曜日ベースフォールバック。最大探索範囲を設定して無限ループ回避。

- 研究（Research）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - バリュー: PER、ROE（raw_financials からの最新財務データを使用）。
    - DuckDB を利用した SQL ベースの計算、データ不足時は None を返す設計。
  - 特徴量探索・統計ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 (calc_forward_returns)、IC（スピアマンのランク相関）計算 (calc_ic)、ランク化ユーティリティ (rank)、ファクター統計要約 (factor_summary)。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
  - research パッケージの公開 API を __init__ で整理・再エクスポート。

- AI（自然言語処理）機能
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini, JSON mode) を使って銘柄別センチメントを算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの記事数・文字数制限（トリム）を実装。
    - レスポンス検証ロジック（JSON パース、results の存在確認、コード照合、数値検証）を実装。
    - 失敗／部分失敗に対するフェイルセーフ設計（API失敗時は当該チャンクスキップ、全体で空なら 0 を返す）。
    - DuckDB への置換書き込みは部分的に安全に行う（DELETE → INSERT、executemany の空リスト対策）。
    - API 呼び出し関数 _call_openai_api を分離してテスト時にモック可能。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - prices_daily からのデータ取得は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - OpenAI へのリクエストはリトライ/バックオフ実装、失敗時は macro_sentiment=0.0 にフォールバック。
    - market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - _call_openai_api が独立実装のためモジュール間結合を抑制しテスト容易性を確保。

- 実装上の共通設計方針（全体）
  - ルックアヘッドバイアス防止:
    - 各処理で datetime.today() / date.today() を直接使わない（外部から target_date を与える方式）。
  - DuckDB をデータレイヤーとして中心に利用（SQL + ウィンドウ関数で実装）。
  - OpenAI 連携は gpt-4o-mini を想定、JSON mode を利用して厳密な構造で結果を受け取る。
  - API エラー（レートリミット、接続エラー、タイムアウト、5xx）に対してエクスポネンシャルバックオフ / リトライを実装。
  - スコアは明示的にクリップ（ニュース: ±1.0、レジーム: ±1.0）して安全性を確保。
  - ロギングを広範に導入し、フォールバックや失敗時の挙動を明示。

### Changed
- N/A（初回リリースにつき該当なし）

### Fixed
- N/A（初回リリースにつき該当なし）

### Security
- 環境変数の自動読み込み時に OS 環境変数を保護する protected 設定を導入（.env による上書きを制御）。

---

注記:
- 実装はテスト容易性を意識しており、OpenAI 呼び出しはモック差し替え可能な関数で囲んであります（unittest.mock.patch による置換を想定）。
- DB 書き込みは冪等性を重視して設計されており、部分失敗時に既存データを不必要に削除しない工夫が含まれます。
- この CHANGELOG はソースコードからの推測に基づくため、実際のリリースノートや設計ドキュメントと差異がある可能性があります。必要に応じて追記・修正してください。