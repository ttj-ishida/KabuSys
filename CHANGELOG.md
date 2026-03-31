CHANGELOG
=========

すべての重要な変更をここに記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-31
------------------

Added
- 初期リリースを公開。
- パッケージ構成
  - kabusys パッケージの基本エントリポイントを追加（src/kabusys/__init__.py）。
  - __version__ を "0.1.0" に設定。公開モジュールとして data, strategy, execution, monitoring をエクスポート。
- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートを .git または pyproject.toml を基準に発見するロジックを実装（cwd に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env パーサを強化（export プレフィックス対応、クォート内のバックスラッシュエスケープ、行内コメント処理）。
  - 環境変数の必須取得ヘルパー（_require）と Settings クラスを提供。
    - J-Quants / kabuステーション / Slack / DB パス / 環境モード（development/paper_trading/live）/ログレベル検証等のプロパティを実装。
    - 無効な env / log level 値については明確な ValueError を送出。
- AI 関連機能（src/kabusys/ai/*）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとに記事を連結し、OpenAI（gpt-4o-mini）に JSON モードで投げてセンチメントを取得。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、記事トリミング、スコアクリップ（±1.0）。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフと安全なフォールバック（失敗時は当該チャンクをスキップ）。
    - レスポンス検証ロジックを実装（JSON 復元、results リスト・code/score 検証、未知コード無視）。
    - スコアを ai_scores テーブルへ冪等に書き込む（DELETE → INSERT）。部分失敗時に既存スコアを保護する設計。
    - calc_news_window() を公開し、JST ベースのニュースウィンドウ計算（前日 15:00 ～ 当日 08:30 JST の扱い）を実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して 'bull'/'neutral'/'bear' を判定。
    - DuckDB から prices_daily / raw_news を参照、calc_news_window を利用して記事ウィンドウを抽出。
    - OpenAI 呼び出しをラップし、リトライ・エラー処理（API エラーの種類に応じた挙動）・JSON パースのフォールバックを実装。
    - 計算結果を market_regime テーブルへ冪等に書き込む（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行。
  - テスト容易性: OpenAI 呼び出し個所に差し替えポイント（内部関数）を用意して unittest.mock.patch によるモックが可能。
- 研究（research）モジュール（src/kabusys/research/*）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）等のファクター計算を実装。
    - DuckDB SQL を活用して効率的に計算し、欠損・データ不足時は None を返す設計。
    - 各関数は prices_daily / raw_financials テーブルのみ参照し、本番取引 API へのアクセスは一切行わない。
  - feature_exploration.py
    - 将来リターン計算（複数ホライズン対応、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク変換、ファクター統計サマリーを実装。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB のみで実装。
  - research パッケージ __init__ で主要関数を再エクスポート。
- データプラットフォーム（src/kabusys/data/*）
  - calendar_management.py
    - JPX カレンダーの扱い（market_calendar）と営業日関連ユーティリティを実装。
    - カレンダーが未取得の場合は曜日ベースのフォールバックを行い、一貫した next/prev/get_trading_days を提供。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存する夜間バッチ処理を実装。バックフィル・健全性チェックを実装。
  - pipeline.py / etl.py
    - ETL パイプラインの主要ユーティリティ（差分取得、バックフィル、品質チェックの呼び出し等）と ETLResult データクラスを追加。
    - ETLResult は品質問題やエラーを集約でき、to_dict によるログ出力向け整形をサポート。
  - jquants_client, quality 等へ依存しつつ、外部 API 呼び出し失敗時は安全に処理を継続する方針を採用。
- その他
  - 各所で「ルックアヘッドバイアス防止」の設計方針を徹底（datetime.today()/date.today() の直接参照を避け、target_date ベースで計算）。
  - DuckDB を主要なローカル分析データベースとして利用する前提の実装を多数追加。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Removed
- 新規リリースのため該当なし。

Security
- 環境変数（OpenAI API キー、Slack トークン、DB パス等）は Settings で必須チェックを行い、未設定時は ValueError を送出して安全性を確保。
- 自動 .env ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能（テスト用途）。

Notes / 設計方針
- 可観測性: 各主要処理で logger.info/debug/warning を適切に出力するよう実装。
- フェイルセーフ: 外部 API エラーやパース失敗時は例外で全体を停止するのではなく、安全なデフォルト（0 や空辞書）にフォールバックして処理を継続する箇所が多数存在。
- 冪等性: DB への書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT を想定）となるよう実装。
- テスト容易性: OpenAI 呼び出し等の外部依存はモック差し替え可能な構成にしている。

今後の予定（例）
- strategy / execution / monitoring の具体的な売買ロジック・実行エンジンの実装・テスト。
- より詳細な品質チェックルール追加とモニタリング・アラート機能の強化。
- パフォーマンス最適化（大規模データに対する DuckDB クエリチューニング等）。

--- 
この CHANGELOG はコードベースの現状から推測して作成しています。実際のコミット履歴やリリースノートに基づく微調整を推奨します。