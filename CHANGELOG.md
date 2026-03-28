# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: 以下は提示されたソースコードから推測して作成した初期リリースの変更履歴です。実際のコミット履歴ではなく、コードベースに実装されている機能・設計判断・重要な実装上の注意点を要約しています。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-28
初期リリース。日本株のデータ収集・NLP・リサーチ・環境設定を含む自動売買支援ライブラリの基本機能を提供。

### 追加
- 基本パッケージ構成
  - パッケージ名: kabusys（バージョン: 0.1.0）
  - エクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイル（.env / .env.local）の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 行パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート・エスケープ処理、インラインコメント処理に対応）。
  - 環境変数取得ヘルパ: Settings クラスを提供。J-Quants / kabuAPI / Slack / データベースパス / ログ設定などのプロパティを定義。
  - 必須環境変数未設定時は明示的に例外を投げる _require() を用意。
  - KABUSYS_ENV と LOG_LEVEL の入力検証（許可値チェック）を実装。

- AI（NLP）モジュール (src/kabusys/ai)
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（ai_score）を算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB をクエリ）。
    - バッチ処理（1コールあたり最大20銘柄）・1銘柄あたり記事上限や文字数トリムによるトークン肥大化対策を実装。
    - JSON Mode レスポンスの検証・正規化機能（レスポンスの抽出、results 配列の検証、コード・スコアのバリデーション）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - API 失敗時はフォールバック（スキップ）し、処理は継続するフェイルセーフ設計。
    - DuckDB へ冪等的に書き込む処理（DELETE → INSERT、executemany に対する空リストガード）を実装。
    - テスト用フック: _call_openai_api を patch して差し替え可能。
    - 公開関数: score_news(conn, target_date, api_key=None)

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロ経済ニュースの LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼出し（gpt-4o-mini）による macro_sentiment 算出（JSON レスポンス期待）。
    - API 呼出しのリトライ（RateLimit, ネットワーク, Timeout, 5xx を考慮）とフォールバック（失敗時 macro_sentiment=0.0）。
    - レジームスコア合成と閾値によるラベリング、結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス対策: target_date 未満のみを参照し、datetime.today() を参照しない設計。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データプラットフォーム（DuckDB ベース） (src/kabusys/data)
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - JPX マーケットカレンダーの管理と夜間バッチ更新ジョブ（calendar_update_job）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の営業日判定 API を提供。
    - market_calendar が未取得の場合は曜日ベース（土日休み）でフォールバックして一貫性を保つ設計。
    - バックフィル・健全性チェック（未来日が極端に遠い場合はスキップ）を実装。
    - J-Quants クライアント経由で差分取得・保存（jquants_client を利用）を想定。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を提供（取得件数、保存件数、品質チェック結果、エラー情報などを格納）。
    - 差分取得・バックフィル・品質チェックを想定したユーティリティ関数を実装（_get_max_date 等）。
    - jquants_client と quality モジュールを組み合わせた差分取得 → 保存 → 品質チェックの流れを想定。
    - etl モジュールは ETLResult の再エクスポートを提供。

- 研究用ユーティリティ（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）を DuckDB SQL で計算。
    - データ不足時の None 扱い、結果を (date, code) ベースの dict リストで返す。
    - 公開関数: calc_momentum, calc_volatility, calc_value

  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）：複数ホライズンをまとめて取得、入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を自前で計算、サンプル不足時は None。
    - ランク関数（rank）：同順位は平均ランクに変換、丸め誤差対策を実装。
    - ファクター統計サマリ（factor_summary）：count, mean, std, min, max, median を算出。
    - 公開関数: calc_forward_returns, calc_ic, rank, factor_summary

### 変更
- なし（初期リリース。実装に関する設計上の注意点は「追加」に記載）。

### 修正
- なし（初期リリース）。

### 内部（実装上の重要ポイント / テストフック）
- OpenAI 呼び出し部分はモジュールごとに private な _call_openai_api を持ち、ユニットテスト時に patch で差し替え可能。
- LLM レスポンスは JSON Mode を期待するが、現実のレスポンスのばらつきに対して復元ロジック（最外側の {} を抽出）や厳格なバリデーションを実装。
- DuckDB の executemany に対する互換性考慮（空リストを渡さないガード）や、idempotent 書き込み（DELETE→INSERT）を採用。
- ルックアヘッドバイアス対策: 各所で date / target_date を明示的に扱い、datetime.today() 等を使わない実装方針。

### 既知の制約 / 注意点
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY が必要。未指定時は ValueError を送出する。
- .env 自動ロードはプロジェクトルートを検出できない場合スキップされる。
- 一部モジュールは jquants_client / quality 等外部モジュールに依存するため、本ライブラリ単体での動作にはそれらの実装が必要。
- 実運用での発注（strategy / execution / monitoring 等）は __all__ に含まれているが、このリリースで提供されるのは主にデータ・NLP・リサーチ周りの基盤機能。

---

今後の提案（参考）
- リリースごとに機能追加（strategy 実装、実運用向けの execution ラッパー、監視/アラート機能など）を CHANGELOG に追記してください。
- セキュリティ関連（API キーの取扱い・ログに秘密情報が残らないこと）や互換性のポリシーを明示するとよいです。