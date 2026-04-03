# Changelog

すべての重大な変更は Keep a Changelog 準拠で記載します。  
このファイルはコードベース（src/kabusys 配下）の現状から推測して作成した初期の変更履歴です。

フォーマット:
- Unreleased: まだリリースされていない変更（当面は空または今後の計画）
- 各バージョン: 追加(Added)、変更(Changed)、修正(Fixed)、非推奨(Deprecated)、削除(Removed)、セキュリティ(Security)

## [Unreleased]
- 現状のコードベースに対する将来の改善メモ（未リリース）
  - モニタリング・実行モジュール（execution, monitoring）の具体的実装追加
  - テストカバレッジ拡充（API呼び出し部分のモック検証等）
  - ドキュメント・使用例の追記

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装。

### Added
- パッケージ初期化
  - kabusys パッケージの基本エントリポイントを追加（__version__ = 0.1.0、公開 API を __all__ で定義）。

- 設定読み込み / 環境変数管理（kabusys.config）
  - .env / .env.local ファイルをプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - .env パーサの実装: コメント行・export プレフィックス・シングル/ダブルクォート・エスケープ・インラインコメントの扱いに対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数保護（既存 OS 環境変数を上書きしない、.env.local は override）をサポート。
  - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB / 監視 / システム関連設定をプロパティ経由で取得。
  - 必須環境変数未設定時の検出（_require）と値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとの記事をバッチ処理し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込み。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して適切に取得。
    - バッチサイズ制限、1銘柄あたりの記事数・文字数制限（トリム）を実装。
    - API エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフとリトライ、レスポンスの厳密なバリデーション（JSON抽出・結果形式検証）を実装。
    - スコアは ±1.0 にクリップ。部分失敗時も既存スコアを保護するため、対象コードのみを DELETE → INSERT で置換。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（モジュール内の _call_openai_api をモック）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - ma200 の計算は target_date 未満のデータのみを利用しルックアヘッドバイアスを排除。
    - マクロニュースはキーワードフィルタで抽出、LLM 呼び出しは API 失敗時に macro_sentiment=0.0 としてフェイルセーフ継続。
    - OpenAI 呼び出しに対するリトライ/バックオフとレスポンスパースの例外処理を実装。
    - DB への書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理、失敗時は ROLLBACK（失敗ログあり）を行う。

- データ / ETL（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジックを実装。
    - market_calendar が未取得時は曜日（平日のみ営業日）をフォールバックする一貫性設計。
    - 夜間バッチ更新 calendar_update_job を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - 異常検出（未来日付の健全性チェック、バックフィル再取得）を実装。

  - pipeline / ETLResult
    - ETLResult データクラスを定義し、ETL の取得数・保存数・品質問題・エラー等を集約して返却・追跡可能に。
    - pipeline モジュール基盤（差分更新、backfill、品質チェックフレームワーク想定）を実装するためのユーティリティを追加。
    - data.etl で ETLResult を再エクスポート。

- 研究向けユーティリティ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金等）、バリュー（PER, ROE）を DuckDB 上で計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足は None を返す安全設計。SQL＋ウィンドウ関数を活用。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を持たず標準ライブラリのみで実装。ランク付けは同順位を平均ランクで処理。

### Changed
- （初回公開）プロジェクト設計方針をコード内に文書化:
  - ルックアヘッドバイアス防止（date.today() など直接参照しない設計）
  - API失敗時に処理を継続するフェイルセーフの徹底
  - DuckDB を主要なデータストアとして明示
  - テストを意識した差し替え可能な内部呼出し（_call_openai_api など）

### Fixed
- （該当なし）初回リリースのため該当なし

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- OpenAI API キーやその他機密情報は環境変数から取得。必須キー未設定時は ValueError を発生させることで誤動作を防止。
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

---

注記:
- 本 CHANGELOG はソースコードからの推定に基づくものであり、実際のコミット履歴を反映したものではありません。リリース時には実際のバージョン管理（git タグ・コミットメッセージ）に基づいて更新してください。