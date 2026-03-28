# CHANGELOG

すべての重要な変更を逐次記録します。本ログは Keep a Changelog の形式に準拠します。

- 変化の分類:
  - Added: 新機能
  - Changed: 変更
  - Fixed: 修正
  - Deprecated: 非推奨
  - Removed: 削除
  - Security: セキュリティに関する変更

## [Unreleased]

（現在未リリースの変更点はここに記載）

---

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能群を実装しました。主要な追加点、設計方針、フェイルセーフやテスト性を考慮した実装などを含みます。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン `0.1.0` を __init__.py に定義。
  - 公開サブパッケージ: data, research, ai, execution, strategy, monitoring をエクスポートする設計（__all__）。

- 設定と環境変数管理（src/kabusys/config.py）
  - .env ファイルと環境変数を統合して読み込む自動ローダを実装。
    - ロード優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（cwd 非依存）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env のパースは export 句、クォート、エスケープ、インラインコメント等に対応する堅牢な実装。
  - 必須環境変数取得のための _require() と Settings クラスを提供（J-Quants、kabuステーション、Slack、データベースパス、実行環境、ログレベル等の設定）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値検査）と利便性プロパティ（is_live / is_paper / is_dev）。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価。
    - バッチサイズ、記事/文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密バリデーション、スコアの ±1.0 クリップ、部分失敗時の DB 保護（対象コードのみ DELETE→INSERT）を実装。
    - calc_news_window(target_date) により JST を基準にしたニュース収集ウィンドウ計算を提供（ルックアヘッドバイアス回避）。
    - テスト容易性を考慮し _call_openai_api を差し替え可能に実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - LLM 呼び出しに対する再試行/エラー処理、API 失敗時のフェイルセーフ（macro_sentiment=0）、JSON パース堅牢化。
    - ルックアヘッドバイアスの回避（date 引数ベース、datetime.today() を参照しない）と DB クエリで target_date 未満のデータのみを使用。

- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）
    - Volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率
    - Value: PER（EPS が 0/欠損 の場合は None）、ROE（raw_financials から）
    - DuckDB の SQL を活用した高性能な実装。結果は (date, code) をキーとする辞書リストで返却。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）のリターンを計算、入力バリデーションあり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（同順位は平均ランク）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を標準ライブラリで算出。
    - ランク変換ユーティリティ（rank）: ties の平均ランク処理と丸めを適用。

- Data プラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの利用による営業日判定・前後営業日検索（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録がない場合は曜日（週末）ベースのフォールバック実装。最大探索日数制限で無限ループ回避。
    - calendar_update_job により J-Quants から差分取得し冪等的に保存、バックフィルと健全性チェックを実装。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを導入して ETL 実行結果、品質問題、エラー情報を集約・辞書化可能に。
    - 差分更新、バックフィル、品質チェックとの連携を想定したユーティリティ関数を実装。
    - jquants_client と quality モジュールとの連携を想定した設計（ID 注入やテスト容易性を考慮）。
  - 公開エントリ（src/kabusys/data/__init__.py, etl.py）で ETLResult を再エクスポート。

- テスト性と設計上の配慮
  - ルックアヘッドバイアス対策: 日付依存処理はすべて target_date 引数ベースで実装し、datetime.today()/date.today() を直接参照しない。
  - API 呼び出し部分は差し替え可能（モック）にして単体テスト容易化。
  - DB 書き込みは冪等操作（DELETE→INSERT、ON CONFLICT 等）を想定・実装して部分失敗時のデータ保護を実現。
  - OpenAI 呼び出しでの堅牢なリトライ／フェイルセーフ（429/ネットワーク/タイムアウト/5xx を考慮）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数管理で必須キー未設定時に明確な ValueError を投げる実装により、秘密情報未設定のまま実行されるリスクを低減。

---

著記の実装は各モジュールの docstring と関数実装に基づいて推測・要約しています。実運用・拡張に際してはドキュメントの追記、単体／統合テスト、設定ファイル（.env.example など）やマイグレーション手順の整備を推奨します。