# Changelog

すべての注目すべき変更点を記載します。本ドキュメントは「Keep a Changelog」形式に準拠します。

リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-28
初回公開リリース。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として定義（src/kabusys/__init__.py）。
  - パッケージ公開 API を __all__ で定義（data / strategy / execution / monitoring）。

- 環境変数・設定管理
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装（src/kabusys/config.py）。
  - 自動 .env ロード機構:
    - プロジェクトルートを .git または pyproject.toml から探索して .env, .env.local を読み込む。
    - .env.local は .env より優先して上書きする挙動を採用。
    - OS 環境変数を保護する仕組み（protected set）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーで以下に対応:
    - コメント行、先頭の export キーワード、シングル/ダブルクォート（バックスラッシュエスケープ対応）、インラインコメントの扱い（クォートなしでは直前が空白/タブの場合に '#' をコメントと認識）。
  - 必須環境変数取得用のヘルパー（_require）。
  - 設定項目（J-Quants トークン、kabuステーション設定、Slack、DB パス、環境モード、ログレベルなど）とバリデーション（有効な env/log_level 値チェック、is_live/paper/dev 補助）。

- AI モジュール（自然言語処理 / レジーム判定）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）:
    - raw_news と news_symbols を使い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを取得。
    - time window（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事選定（UTC 変換を内部で扱う）。
    - 1 チャンク最大 20 銘柄でバッチ送信、1 銘柄あたり最大記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode を使った堅牢なレスポンスパースと復元処理（余計な前後テキストが混在する場合の {} 抽出）。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフ（最大リトライ回数と待機時間の設定）。
    - レスポンス検証: results 配列、code の検証、スコアの数値化・有限性チェック、±1.0 でクリップ。
    - 書き込みは冪等処理（部分失敗時に他銘柄スコアを保護するため DELETE → INSERT をコード単位で実行）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）:
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、ニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次で regime（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタし、最大 N 記事を LLM に送信して JSON レスポンスから macro_sentiment を抽出（gpt-4o-mini）。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - API エラー時はフォールバック macro_sentiment = 0.0、リトライ／バックオフ戦略を実装。
    - 最終的なスコアはクリップされ、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。

- データ（Data platform）モジュール
  - カレンダー管理（src/kabusys/data/calendar_management.py）:
    - market_calendar を元に営業日判定・前後営業日検索・期間内営業日取得・SQ日判定を提供。
    - DB 登録値を優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - next_trading_day / prev_trading_day は最大探索日数制限を設け、無限ループを防止。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants から差分取得して冪等的に保存、バックフィル期間の再取得、健全性チェック（過度に将来の日付はスキップ）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）:
    - ETLResult データクラスを定義（target_date、取得/保存件数、品質チェック結果、エラー一覧等）。
    - 差分更新のロジック、backfill の適用、J-Quants クライアント（jquants_client）経由の保存、品質チェック（quality モジュール）との統合設計。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得などを実装。
  - ETL 公開インターフェース（src/kabusys/data/etl.py）:
    - pipeline.ETLResult を再エクスポート。

- Research（リサーチ）モジュール
  - factor_research（src/kabusys/research/factor_research.py）:
    - Momentum（1M/3M/6M リターン・200 日 MA 乖離）、Value（PER・ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金・出来高比率）を計算する関数群（calc_momentum / calc_value / calc_volatility）。
    - DuckDB の SQL ウィンドウ関数を利用した実装。データ不足時は None を返す方針。
  - feature_exploration（src/kabusys/research/feature_exploration.py）:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を提供。
    - 外部依存を持たず標準ライブラリと DuckDB のみで実装。horizons のバリデーションや ties の平均ランク処理などを考慮。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

---

注記:
- OpenAI 連携部分は API キー注入（引数 or 環境変数 OPENAI_API_KEY）をサポートし、テスト時の差し替えを想定した設計になっています。
- いくつかの処理（DB 書き込み、API 呼び出し）はフォールバックや冪等性を重視しており、本番運用での堅牢性を意図しています。
- 各モジュールは DuckDB 接続を受け取りローカル DB を直接操作する設計で、外部取引 API（実際の発注等）にはアクセスしない境界を明確にしています。