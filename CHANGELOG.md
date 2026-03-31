# Changelog

すべての日付は ISO 形式（YYYY-MM-DD）で記載しています。本ドキュメントは「Keep a Changelog」フォーマットに準拠しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装しました。主な追加点と設計方針は以下の通りです。

### Added
- パッケージ基礎
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンは 0.1.0。
  - 公開サブパッケージのプレースホルダ（data, strategy, execution, monitoring）を定義。

- 環境設定 / ロード処理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - 読み込み優先度: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト支援）。
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索して判定（CWD 非依存）。
  - .env パーサを実装（コメント行、export 前置、クォート中のエスケープ、インラインコメント処理などに対応）。
  - Settings クラスを提供し、必須環境変数チェック（_require）、既定値、型変換（Path/float）や列挙値チェックを実装。
    - 必須項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - システム設定: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL 検証
    - 監視閾値等の設定（PID ファイル、CPU/MEM/DISK 閾値、DB パス既定値など）

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）の JSON Mode を使い銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの記事/文字数上限、チャンクごとのリトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列・code/score 検証、数値変換、スコアクリップ）。
    - ai_scores テーブルへの冪等更新（該当コードのみ DELETE → INSERT）を実装。DuckDB 0.10 の executemany 空リスト制約に配慮。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
    - タイムウィンドウ: target_date の「前日 15:00 JST ～ 当日 08:30 JST」を UTC に変換して扱う（ルックアヘッドバイアス回避）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定。
    - ma200 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）、不足時は中立扱い。
    - マクロニュースは news_nlp の calc_news_window と raw_news を用いて抽出。OpenAI 呼び出しは独立実装。
    - OpenAI 呼び出しに対するリトライ（RateLimit/接続タイムアウト/API 5xx に対する指数バックオフ）とフォールバック（失敗時 macro_sentiment=0.0）を実装。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して上位へ例外を伝播。

- Data プラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - 営業日判定ユーティリティ群を実装: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB にデータがない場合は曜日ベースのフォールバック（平日＝営業日）を行い、一貫性を保つ実装。
    - 探索上限（_MAX_SEARCH_DAYS）や先読み／バックフィル／健全性チェック（未来日付の異常検出）を導入。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（ETL のフェッチ数・保存数、品質問題、エラー一覧を収集）。
    - 差分更新・バックフィル方針、品質チェック連携、id_token 注入によるテスト容易性などを実装方針として採用。
    - etl.py で pipeline.ETLResult を再エクスポート。

  - DB/ユーティリティ
    - DuckDB を前提とした SQL 実装。テーブル存在確認や日付取り扱いユーティリティを多数実装。

- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（データ不足は None）。
    - ボラティリティ/流動性: 20 日 ATR（true_range の NULL 伝播を考慮）、相対 ATR、20 日平均売買代金、出来高比。
    - バリュー: raw_financials から最新財務を取得し PER/ROE を算出（EPS=0 の場合は None）。
    - すべて prices_daily / raw_financials のみ参照し、DB 内で完結する設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン (forward returns) の一括算出（任意ホライズン、ホライズン検証）。
    - IC（Spearman の ρ）計算（ランク変換は平均ランク、同順位の扱いあり）。有効レコードが 3 未満の場合 None を返す。
    - factor_summary: count/mean/std/min/max/median を算出する統計ユーティリティ（None は除外）。
    - rank ヘルパー関数を提供（round による ties 対策）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- （該当なし）

### Notes / 設計上の重要なポイント
- ルックアヘッドバイアス防止: すべての分析/スコアリング関数は内部で date.today() を直接参照せず、target_date 引数に依存する設計としています。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定し JSON Mode（response_format={"type": "json_object"}）で利用。
  - API の一時エラーや 5xx に対する再試行とフォールバック（安全側のデフォルト値）を明確化。
  - テスト時の差し替えを容易にするため _call_openai_api を経由する設計。
- DuckDB 依存:
  - SQL の書き方や executemany の扱いに DuckDB バージョン依存の注意点（空リスト渡し不可等）を反映しています。
- 冪等性:
  - DB 書き込みは可能な限り冪等に行う（DELETE→INSERT、ON CONFLICT の利用など）ことで部分失敗時のデータ保護を意識しています。

---

開発者向けにさらに詳細な差分・API 使用例・DB スキーマの説明が必要であれば、用途別（AI スコアリング、ETL、ファクター計算、カレンダー運用）に分けた追加のドキュメントやサンプルを作成します。必要な場合はどの領域を優先するか教えてください。