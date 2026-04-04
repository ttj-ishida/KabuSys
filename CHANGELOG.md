# CHANGELOG

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」規約に準拠します。

フォーマット:
- Unreleased: 現在進行中の変更（必要に応じて更新）
- 各リリースは日付付きで記載

なお、本CHANGELOGは提供されたコードベースの実装内容から推測して作成しています。

## [Unreleased]
- 次回リリースに向けた未定義の改善・追加点（ドキュメント整備、テストケースの拡充、エラー時の監視強化など）。

## [0.1.0] - 2026-04-04
最初の公開リリース。日本株自動売買システムのコアライブラリを実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを初期実装。バージョン情報を `__version__ = "0.1.0"` で管理。
  - パッケージ公開 API のための __all__ 定義（data, strategy, execution, monitoring）。

- 設定・環境管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数からの設定読み込み機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）により CWD に依存しない .env 自動読み込みを行う。
  - 読み込み優先順位を OS 環境変数 > .env.local > .env と規定し、.env.local は上書き（override）される実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーは export 形式、シングル/ダブルクォート、エスケープ、行内コメントの扱いなどに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE API / DB パス / 監視閾値 / 環境設定（development, paper_trading, live）などのプロパティを取得可能。未設定の必須環境変数は明確なエラーメッセージで通知。

- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュースセンチメント分析 (news_nlp.score_news)
    - raw_news / news_symbols テーブルを使い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）の JSON mode へバッチ送信する。
    - 時間ウィンドウは JST 基準で「前日 15:00 〜 当日 08:30」（UTC 換算）を採用。calc_news_window ユーティリティを提供。
    - 1チャンクあたり最大銘柄数、最大記事数、最大文字数等のトークン肥大化対策を実装（バッチ処理, トリム）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。非再試行エラーはスキップして処理継続（フェイルセーフ）。
    - レスポンスの堅牢なバリデーションと JSON パースの復元処理（前後余分テキストから {} を抽出）を実装。無効レスポンスや未知コードは無視。
    - 成果は ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出しコードは差し替え可能（ユニットテストでの patch を想定）。

  - 市場レジーム判定 (ai.regime_detector.score_regime)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（70%）とマクロセンチメント（30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出はキーワードベース（日本・米国・グローバルの主要語）でタイトルを取得し、OpenAI に JSON 出力を要求してセンチメントを得る。
    - 計算式: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
    - OpenAI API 呼び出しのリトライ・5xx 処理を実装。API 失敗時は macro_sentiment=0.0 にフォールバックして継続（フェイルセーフ）。
    - market_regime テーブルへの書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に実行。失敗時は ROLLBACK を試み、失敗ログを出力。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダー管理機能を実装し、営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を提供。
    - market_calendar が未取得のときは曜日（週末除外）ベースのフォールバックを行う設計で、DB 登録値があれば優先使用。
    - next/prev_trading_day の探索は最大探索日数を設定して安全に動作（無限ループ防止）。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得・バックフィル（直近日数の再取得）・保存（idempotent）を実行。健全性チェックで不自然に未来の日付がある場合はスキップ。
    - jquants_client との連携を想定（fetch / save 関数呼び出し）。

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開し、ETL 実行結果（取得数・保存数・品質チェック・発生エラー）を構造化して返却。
    - 差分更新、バックフィル、品質チェックを行う設計方針をコードドキュメントで明示。
    - データ保存は jquants_client の save_* 関数を呼び idempotent に保存する方針。

- リサーチ / ファクター解析 (kabusys.research)
  - factor_research
    - Momentum, Volatility, Value, Liquidity 等の定量ファクターを実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出（EPS 不在時は None）。
    - 全関数は DuckDB 接続を受け取り、参照テーブルは prices_daily / raw_financials のみ（本番発注 API へはアクセスしない）。
  - feature_exploration
    - calc_forward_returns: 各種ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算。ホライズン検証（1..252）あり。
    - calc_ic: スピアマンのランク相関（IC）を計算。データ不足（有効レコード < 3）時は None。
    - rank: 同順位は平均ランクを返すランク付け関数を実装（丸めで ties 対策）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算する統計サマリー。

- 共通実装 / 設計上の注意点
  - DuckDB をデータストアに採用しており、SQL + Python の組合せで計算・集計を実行。
  - ルックアヘッドバイアス防止のため、各モジュールは datetime.today()/date.today() を直接参照せず、target_date 引数に基づいて処理する設計。
  - OpenAI 呼び出し箇所はテストで差し替え可能にしている（ユニットテスト容易化）。
  - DB 書き込みは冪等化（DELETE→INSERT や ON CONFLICT を想定）し、部分失敗時に既存データを不必要に消さない実装方針。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- なし。

### セキュリティ (Security)
- OpenAI API キーや各種外部サービスの資格情報は環境変数に依存。必須の環境変数が未設定の場合は明確に ValueError を送出して処理を停止する箇所があるため、運用時の秘匿管理に注意が必要。

---

注記:
- 上記はソースコードの実装内容から機能・設計・注意点を抽出した CHANGELOG です。リリース日付は現時点（2026-04-04）を使用していますが、実際のリリース運用に合わせて日付・バージョンは適宜調整してください。