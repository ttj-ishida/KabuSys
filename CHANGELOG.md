# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  

※このファイルはコードベースの内容から推測して作成しています。

## [Unreleased]
（次リリースに向けた変更はここに記載します）

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買システムのコア機能群を実装・公開しました。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを `0.1.0` に設定。公開モジュールとして data, strategy, execution, monitoring を __all__ に定義。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を起点に探索）。CWD に依存しない実装。
  - .env パーサーを実装:
    - 空行・コメント行（#）の無視、`export KEY=val` 形式の対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなし値に対するインラインコメント判定（直前が空白/タブの場合にコメント扱い）。
  - .env 自動読み込み順序: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
  - 設定取得用 `Settings` クラスを実装（J-Quants トークン、kabu API、LINE、DB パス、監視・閾値設定など）。
  - 設定のバリデーション（KABUSYS_ENV, LOG_LEVEL 等の許容値チェック）と便利プロパティ（is_live/is_paper/is_dev）。

- AI: ニュース NLP (`kabusys.ai.news_nlp`)
  - raw_news → 銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント（-1.0〜1.0）を銘柄別に評価する `score_news` を実装。
  - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を実装する `calc_news_window`。
  - バッチ処理、1チャンク当たり最大20銘柄、1銘柄あたり最大10記事・3000文字でトリムする仕組み。
  - API 呼び出しのリトライ（429、ネットワーク断、タイムアウト、5xx）と指数バックオフ処理、失敗時のフォールバック動作。
  - レスポンスの堅牢なバリデーションと復元処理（JSON 以外の余計な前後テキストを考慮して {} を抽出）を実装。
  - スコアは ±1.0 にクリップ。DuckDB への書き込みは置換（DELETE→INSERT）で冪等性を確保。部分失敗時に他の銘柄データを消さない構成。
  - テスト容易性を考慮し、OpenAI 呼び出し部分を差し替え可能（ユニットテスト用にモック可能）。

- AI: 市場レジーム判定 (`kabusys.ai.regime_detector`)
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する `score_regime` を実装。
  - マクロキーワードで raw_news をフィルタしてタイトルを抽出し、OpenAI（gpt-4o-mini）でマクロセンチメントを算出。
  - API エラーやパース失敗時は macro_sentiment = 0.0 としてフェイルセーフで継続。
  - レジームスコアの合成・クリップ・ラベリング後、`market_regime` テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - 設計上、ルックアヘッドバイアスを防ぐために date 未満のデータのみ参照し、date.today() 等を直接参照しない実装。

- 研究系モジュール (`kabusys.research`)
  - factor_research:
    - モメンタム（1m/3m/6m リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高変化率）、バリュー（PER, ROE）を計算する関数群を実装:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB を用いた SQL ベースの計算。必要行数不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - pandas 等に依存せず、標準ライブラリのみで実装。入力データの検証や ties 処理（平均ランク）に配慮。
  - 研究用ユーティリティの再エクスポート（zscore_normalize 等）を行う __init__。

- データ管理モジュール (`kabusys.data`)
  - calendar_management:
    - JPX カレンダー管理（market_calendar）を扱うユーティリティを実装。
    - 営業日判定（is_trading_day）、SQ判定（is_sq_day）、次/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）を提供。
    - DB の calendar データが無い場合は曜日ベース（平日）でフォールバックする一貫性のある設計。
    - 夜間バッチ更新用の `calendar_update_job` を実装し、J-Quants クライアント経由で差分取得・冪等保存（fetch/save）を行う。バックフィルや健全性チェックを実施。
  - ETL / pipeline:
    - ETL パイプラインの結果を表す `ETLResult` データクラスを実装（取得件数、保存件数、品質問題リスト、エラー一覧等を保持）。
    - ETL の振る舞い（差分取得、バックフィル、品質チェックの収集方針）に関する設計方針を明記。
    - ETLResult を外部へ公開（`kabusys.data.etl` から再エクスポート）。

- テスト性・堅牢性設計
  - OpenAI API 呼び出し部分はモジュール内で分離し、ユニットテストで差し替え可能に実装。
  - DuckDB を前提とした SQL 実行での空リスト executemany 対応（DuckDB のバージョン依存性に配慮）や ROLLBACK の失敗をログに残す等、運用上の堅牢性を確保。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数や API キーは環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）から取得する設計。`.env` の自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

参考・設計上の注意点（コード内コメントの要約）
- ルックアヘッドバイアス防止のため、日次計算関数は常に target_date 引数に基づき過去データのみを参照し、datetime.today()/date.today() を直接参照しない。
- OpenAI など外部 API の障害は致命的な例外をすぐに投げず、スコアのデフォルト値（0.0）で継続するなどフェイルセーフ設計。
- DuckDB 固有の挙動（executemany の空リスト不可など）を考慮した実装。
- news_nlp と regime_detector は OpenAI 呼び出し実装を分離しており、モジュール間でプライベート関数を共有しない設計（モジュール結合を避ける）。

（以上）