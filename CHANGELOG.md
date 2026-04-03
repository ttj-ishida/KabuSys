# Changelog

すべての変更は Keep a Changelog 規約に準拠します。  
このプロジェクトの初回公開リリースは v0.1.0 です。

注: 以下はリポジトリ中のソースコードから推測してまとめた変更点・機能説明です（自動生成的ドキュメント）。実際のリリースノートとして使用する場合は運用上の要件や既知の制約を併せて確認してください。

## [Unreleased]
（次回リリースに向けた追加・調整事項をここに記載してください）

---

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買システム基盤のコアモジュールを提供します。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン: 0.1.0）。公開モジュール: data, strategy, execution, monitoring（__all__ による）。
- 設定・環境管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みするユーティリティを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点に探索）により CWD 非依存で動作。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - .env パーサは export 形式・クォート・インラインコメント・エスケープ等に対応。
  - Settings クラスを提供（プロパティ経由で各設定にアクセス）。
    - J-Quants、kabuステーション、LINE、DBパス、監視閾値、実行環境判定(is_live / is_paper / is_dev) などを集約。
    - 値検証（KABUSYS_ENV, LOG_LEVEL 等）を備える。
- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理、営業日判定、next/prev_trading_day、get_trading_days、SQ判定、夜間バッチ更新ジョブ(calendar_update_job) を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - API から差分取得→冪等保存を行い、バックフィル・健全性チェックを実装。
  - pipeline / ETL: ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETL の成果（取得数、保存数、品質問題、エラー等）を集約して返す型を提供。
    - 差分更新・バックフィル設計（デフォルトbackfill日数等）や品質チェックとの連携を想定。
- AI 関連（kabusys.ai）
  - news_nlp: ニュース記事に対するセンチメント付与ロジックを実装。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチ評価（1チャンクで最大20銘柄）。
    - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
    - 銘柄ごとに記事を集約し、文字数・記事数制限（トリム）を実施。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）は指数バックオフで実装。API レスポンス検証とスコアクリップ（±1.0）。
    - DuckDB の executemany 空リスト制約への対応（空のときは呼ばない）。
    - テスト容易性のため _call_openai_api のモック差し替えポイントを用意。
  - regime_detector: マーケットレジーム判定（bull / neutral / bear）を実装。
    - ETF 1321（Nikkei 225 連動 ETF）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成。
    - LLM 呼び出しは gpt-4o-mini を使用し、JSON パース・リトライ・フェイルセーフ（API 失敗時は macro_sentiment = 0.0）を実装。
    - データベースへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - ルックアヘッドバイアス対策（target_date 未満のデータのみ使用、datetime.today() を参照しない）。
- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数を実装。
    - DuckDB SQL を活用した高速集計と、データ不足時の None ハンドリングを行う。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（スピアマンρ）算出 calc_ic、値をランクに変換する rank、ファクター統計 summary を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で完結する設計。
- その他実装上の設計・品質点
  - DuckDB 互換性を考慮した実装（executemany の空リスト回避、date の扱い変換ユーティリティ等）。
  - API キー注入を多数の関数でサポート（api_key 引数を優先、未指定時は OPENAI_API_KEY 環境変数を参照）し、テストやオーケストレーションでの鍵管理を容易化。
  - 多くの場所でフェイルセーフ（API 失敗時に処理を継続、警告ログを出す）を採用し運用安定性を重視。

### Changed
- 新規リリースのため該当なし（初版）。

### Fixed
- 新規リリースのため該当なし（初版）。

### Security
- OpenAI / 外部 API キーは環境変数で管理する設計（明示的にハードコードしない）。

### Migration / 注意事項
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
  - OPENAI_API_KEY（news_nlp / regime_detector の呼び出し時に必要。関数呼び出しで api_key を明示的に渡すことも可能）
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（CI/テスト用途）。
- DuckDB のバージョン差異により配列や list バインドの挙動が異なる可能性があるため、ETL / ai_scores 書き込み処理では executemany を用いた互換性重視の実装になっています。
- LLM（OpenAI）呼び出しは料金とレイテンシを伴います。ローカルテスト時は _call_openai_api をモックすることを推奨します。
- 全モジュールはルックアヘッドバイアス（未来データの参照）を避ける設計方針を採用しています。運用時も target_date を適切に渡してください。

---

もし追加で各モジュールの簡易 API サンプル（使い方）や、リリースに含めるスクリーンショット／ログ例が必要であればお知らせください。