# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のガイドラインに従って記載しています。  
このファイルはコードベースの内容から推測して作成した初回リリース向けの変更履歴です。

全般的な方針
- 日付はリポジトリ内の __version__ およびコードの設計方針（ルックアヘッドバイアス防止・フェイルセーフ等）を踏まえ推定しています。
- DuckDB を内部データストアとして想定した実装、OpenAI（gpt-4o-mini）を用いた NLP 機能、J-Quants クライアント連携の ETL / カレンダ処理などを含みます。

Unreleased
- （なし）

0.1.0 - 2026-03-31
Added
- パッケージの初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開API（__all__）に data, strategy, execution, monitoring を定義。

- 環境設定管理モジュール (kabusys.config) を追加。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装: export 形式対応、シングル/ダブルクォートのエスケープ処理、インラインコメントの扱いの適切化。
  - 環境変数取得ユーティリティ _require と Settings クラスを提供（各種 API トークン、DBパス、監視閾値、実行環境判定等）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）を実装。

- AI（自然言語処理）関連モジュールを追加 (kabusys.ai)。
  - news_nlp.score_news
    - raw_news と news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメント（ai_scores）を取得・保存。
    - バッチサイズ、記事数・文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1 クリップ、部分的な DB 書換（DELETE → INSERT）により堅牢に処理。
    - テスト容易性のため _call_openai_api を外部差替え可能（unittest.mock.patch を想定）。
    - ニュースウィンドウの計算（JSTベース → UTC naive datetime）を calc_news_window で提供。ルックアヘッドバイアスを回避する設計。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルに冪等書き込み。
    - マクロセンチメントは raw_news からマクロキーワードで抽出したタイトルを LLM に投げて算出。API 障害時は安全に macro_sentiment=0.0 にフォールバック。
    - OpenAI 呼び出しのリトライ戦略、JSON レスポンスパースの堅牢化、スコアのクリップ、DB トランザクション（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK）を実装。

- リサーチ機能群を追加 (kabusys.research)。
  - factor_research
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離の算出（データ不足時の挙動明示）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを算出。
    - calc_value: raw_financials からの EPS/ROE を組み合わせて PER/ROE を計算（財務データが無い/ゼロの場合の取り扱い）。
    - DuckDB を用いたウィンドウ関数中心の実装、外部 API への依存なし、date を基準にしたルックアヘッド回避。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分なサンプル数がない場合は None を返す。
    - rank: 平均ランク（同順位は平均ランク）の実装（丸め処理で ties の安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを標準ライブラリのみで実装。
  - research パッケージは zscore_normalize（kabusys.data.stats 由来）等を再エクスポート。

- データプラットフォーム関連モジュールを追加 (kabusys.data)。
  - calendar_management
    - JPX カレンダー管理 API（J-Quants 連携）を想定した夜間更新ジョブ calendar_update_job。
    - market_calendar を参照した is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day のロジックを提供。DB 登録値優先、未登録日は曜日ベースでフォールバック。
    - 最大探索日数の上限設定、バックフィル・健全性チェック等を実装。
  - pipeline / etl
    - ETLResult データクラスを定義し、kabusys.data.etl で公開。
    - ETL パイプラインの設計（差分取得、保存、品質チェック）を反映するユーティリティの骨子を実装（J-Quants クライアント置換可能、品質チェック収集型の挙動）。
    - DuckDB テーブル存在チェックや最大日付取得などの内部ユーティリティを実装。

- その他
  - モジュール設計で「日付・時間はすべて timezone-naive の date / datetime を利用する」「datetime.today()/date.today() を参照しない（ルックアヘッドバイアス防止）」などの設計方針を各所に明記。
  - OpenAI 呼び出しに対して JSON mode を使い厳密な JSON 出力を期待するプロンプト設計と、レスポンスパースにおける復元ロジック（外側の {} を抽出）を実装。
  - 重要な処理（AI 呼び出し、DB 書き込み）に対して WARN/INFO/DEBUG ログを適切に出力。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- API キーや機密情報は明示的に Settings 経由で取得する設計。自動 .env ロード時も既存 OS 環境変数を保護するため protected セットを採用。

Notes / 実装上の注意点（ユーザへの補足）
- OpenAI API キーは api_key 引数を優先、未指定時は環境変数 OPENAI_API_KEY を参照する設計。未設定時は ValueError を送出する実装。
- テスト容易性のため、OpenAI 呼び出し部は内部関数を patch して差し替え可能（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- DuckDB についてはバージョン互換性の注意（executemany に空リストを渡せない等）を考慮した実装になっている。
- 本 CHANGELOG はコードベースの内容から推測して作成したものであり、実際のコミット履歴とは異なる場合があります。