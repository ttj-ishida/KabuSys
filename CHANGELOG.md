# Changelog

すべての notable な変更点をこのファイルに記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース。以下の主要機能を実装・公開しました。

### Added
- 基本パッケージ
  - パッケージのバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。
  - パッケージ外部公開 API を `__all__ = ["data", "strategy", "execution", "monitoring"]` として定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの設定読み込み機能を追加。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により、CWD に依存しない自動 .env ロードを実現。
  - .env パーサ実装（コメント、export KEY=val 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い等に対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は上書き保護（protected）。
  - 自動ロード無効化のためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で使用可能）。
  - 必須環境変数チェック `_require()` を提供し、不足時に分かりやすいエラーメッセージを返す。
  - アプリ設定ラッパー `Settings` を追加し、以下のプロパティ等を提供:
    - J-Quants / kabu ステーション / LINE / データベースパス（DuckDB/SQLite）/監視設定（PID ファイル、kill フラグ、閾値）/システム環境（env, log_level, is_live 等）。
  - `KABUSYS_ENV` と `LOG_LEVEL` の入力検証（許容値集合チェック）を実装。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（score_news）
    - raw_news と news_symbols を使って銘柄ごとに記事を集約し、OpenAI を用いてセンチメント（-1.0〜1.0）を算出、`ai_scores` テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）を正しく計算する `calc_news_window()` を提供。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、記事・文字数トリム（記事数・文字数閾値）によりトークン肥大を抑制。
    - OpenAI への JSON Mode 出力期待、レスポンスの堅牢なバリデーション（JSON 抽出、results 配列チェック、コード正規化、数値チェック）を実装。
    - リトライ戦略（429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ）を実装。致命的でない失敗はフェイルセーフによりスキップ継続。
    - DuckDB の executemany の挙動（空リスト不可）や部分失敗時の既存スコア保護（対象コードの絞り込み DELETE → INSERT）を考慮した書き込みロジックを実装。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（unittest.mock.patch で _call_openai_api をモック可能）。
  - レジーム判定（score_regime）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して、日次レベルで市場レジーム（bull / neutral / bear）を判定する処理を実装。
    - prices_daily から MA200 の乖離を計算する `_calc_ma200_ratio()`、raw_news からマクロキーワードに一致するタイトルを抽出する `_fetch_macro_news()` を実装。
    - OpenAI 呼び出しの堅牢なリトライ／フォールバック（API 失敗時は macro_sentiment = 0.0）を組み込み。
    - レジームスコアのクリップ、閾値判定、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時の ROLLBACK）の実装。
    - ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を参照しない設計）。

- リサーチ機能（src/kabusys/research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）を計算する関数群を実装: `calc_momentum()`, `calc_volatility()`, `calc_value()`。
    - DuckDB SQL を用いた高効率なウィンドウ集計を実装。データ不足時は None を返す挙動。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（`calc_forward_returns()`）、IC（Information Coefficient）計算（`calc_ic()`）、ランク変換ユーティリティ（`rank()`）、統計サマリー（`factor_summary()`）を実装。
    - pandas 等に依存せず、標準ライブラリのみで実装。
  - research パッケージの __init__ で主要関数を再公開（使いやすいトップレベル API）。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（calendar_management）
    - JPX カレンダー取り扱い機能（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar テーブルが未取得のときは曜日ベースのフォールバック（週末は非営業日）を行い、DB 登録ありの場合は DB 値を優先する一貫したロジックを提供。
    - 夜間バッチ更新ジョブ `calendar_update_job()` を実装（J-Quants クライアントから差分取得、バックフィル、健全性チェック、保存）。
    - 最大探索範囲や健全性チェックにより無限ループや異常値を防止。
  - ETL パイプライン（pipeline / etl）
    - ETL 実行結果を表すデータクラス `ETLResult` を実装（取得件数・保存件数・品質問題・エラー一覧などを保持）。`to_dict()` によるシリアライズをサポート。
    - ETL 関連の設計（差分更新、バックフィル、品質チェックの取り扱い）を反映した基盤を実装。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。

- 運用・監視関連
  - 監視・実行制御に関する設定（PID ファイルパス、kill フラグファイル、クリアオンスタート設定、CPU/メモリ/ディスク閾値）を Settings で提供。

### Fixed / Improved
- .env パーサの堅牢性向上
  - クォート内のバックスラッシュエスケープ対応、export プレフィックス処理、コメント判定の改善により現場の .env 慣習に対応。
- OpenAI 呼び出しの堅牢性
  - JSON Mode の出力が前後に余計なテキストを含むケースを考慮し、最外の { ... } を抽出してパースするフォールバック処理を追加。
  - APIError の status_code 取り扱いを安全に行い（getattr）、将来の SDK 変化への耐性を高めた。
- DuckDB 互換性対策
  - executemany に空リストを渡さないガード、リストバインドの不安定性回避のため DELETE を個別実行する実装等、DuckDB の既知制約を考慮。

### Design / Testing notes
- ルックアヘッドバイアス回避を設計方針として明確に適用（各スコア算出は target_date を明示的に受け取り、内部で現在日時を参照しない）。
- テスト容易性を考慮し、OpenAI 呼び出し箇所を差し替え可能に設計（ユニットテストでのモックが可能）。
- フェイルセーフ原則: 外部 API（OpenAI, J-Quants）障害時は可能な限り処理を継続し、致命的な障害のみ上位へ伝播。ログで詳細を残す。

### Security
- 環境変数の読み込みでは OS 環境変数を保護（.env の上書きを防止）する仕組みを導入。

---

今後の予定（例）
- strategy / execution / monitoring パッケージの実装（発注ロジック、実行監視、アラート連携等）。
- テストカバレッジ拡張（AI モジュールのエンドツーエンド試験用のモック基盤等）。
- ドキュメント (API リファレンス、運用手順) の拡充。

（この CHANGELOG はコードベースの実装内容から推測して作成しています。詳細実装や未公開のサブモジュールが存在する場合は実際の変更点と差異がある可能性があります。）