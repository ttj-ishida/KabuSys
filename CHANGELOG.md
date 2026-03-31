# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-31

初回リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。パッケージ版のバージョンは `__version__ = "0.1.0"`。
  - public API エクスポート: `__all__ = ["data", "strategy", "execution", "monitoring"]`。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を起点に探索）。CWD に依存しないためパッケージ配布後も動作。
  - .env パーサー実装（`_parse_env_line`）:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - インラインコメントの取り扱い（クォートあり/なしで挙動を区別）
    - 無効行（空行・コメント・等号なし）をスキップ
  - .env 読み込みの優先順位を OS 環境変数 > .env.local > .env として実装。既存 OS 環境変数は保護（protected）される。
  - `Settings` クラスを追加し、アプリケーション設定をプロパティ経由で提供（J-Quants、kabuステーション、Slack、データベースパス、監視閾値、環境 / ログレベル判定等）。
  - 必須環境変数未設定時は明示的な `ValueError` を送出する `_require` を用意。

- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントスコアを算出する `score_news` を追加。
    - タイムウィンドウの計算ユーティリティ `calc_news_window` を実装（JST基準で前日15:00〜当日08:30に対応、DBはUTCで比較）。
    - チャンク処理（最大 20 銘柄/コール）、1銘柄当たりの記事上限・文字上限（トリム）を導入してトークン肥大化を抑制。
    - API 呼び出しに対して指数バックオフ（429・ネットワーク・タイムアウト・5xx を対象）を実装。
    - レスポンスバリデーション (`_validate_and_extract`) を行い、レスポンスの JSON 抽出（余計な前後テキストの回復処理含む）、型チェック、未知コードの無視、スコアの数値化・有限値検証、±1.0 クリップを実施。
    - DuckDB 互換性を考慮し、`executemany` に空リストを渡さないガードを実装。スコア書き込みは部分置換（対象コードのみ DELETE → INSERT）して部分失敗時に既存データを保護。
    - OpenAI API キー注入を引数で可能にしてテスト容易性を確保。未設定時は `ValueError` を送出。

  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する `score_regime` を追加。
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
    - マクロニュース抽出ロジック（マクロキーワードでフィルタ）と LLM 呼び出しでのセンチメント評価を実装（最大記事数制限、API 再試行・フォールバック）。
    - LLM 呼び出しのリトライ/バックオフ（429/接続/タイムアウト/5xx を考慮）や、API 失敗時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - 計算結果を `market_regime` テーブルに対し冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK と例外伝播）。

  - ai パッケージの __init__ で `score_news` を公開。

- Data / ETL（kabusys.data）
  - calendar_management モジュール
    - JPX 市場カレンダー管理機能を実装。営業日判定ユーティリティ（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを行い、一貫性を担保。
    - カレンダー夜間更新ジョブ `calendar_update_job` を実装（J-Quants API から差分取得・バックフィル・健全性チェック・冪等保存）。
    - 最大探索日数やバックフィル期間、先読み日数、健全性チェック等の安全制約を導入。

  - pipeline / ETL（kabusys.data.pipeline）
    - ETL パイプライン設計（差分取得・保存・品質チェック）を反映。
    - ETL 実行結果を表すデータクラス `ETLResult` を追加（取得数・保存数・品質問題・エラー一覧・ユーティリティ to_dict、エラー判定プロパティ等）。
    - 内部ユーティリティ: テーブル存在チェック、テーブル内最大日付取得などを実装。
    - jquants_client と quality モジュールとの連携を想定（差分取得・保存・品質チェックのフローを定義）。

  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）などファクターを DuckDB 上で計算する関数を実装：`calc_momentum`, `calc_volatility`, `calc_value`。
    - SQL を活用して効率的に計算し、データ不足時の扱い（None 戻し）を明確化。
  - feature_exploration モジュール
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算 `calc_ic`（Spearman のランク相関を自前実装）。
    - `rank`（同順位は平均ランク化）と統計サマリー `factor_summary`（count, mean, std, min, max, median）を追加。
  - research パッケージ __init__ で主要ユーティリティを再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes（実装上の考慮・設計方針）
- ルックアヘッドバイアス防止のため、全てのバッチ処理で内部的に date / target_date を明示的に受け取り、`datetime.today()` / `date.today()` を直接参照しない設計を採用している箇所が多数存在。
- OpenAI 呼び出しはリトライ/バックオフ、レスポンス検証、JSON モードの余白処理など堅牢性を重視して実装。
- DuckDB の互換性問題（リストバインドの不安定性、executemany に空リストを渡せない等）に対するワークアラウンドを採用。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 対応想定）し、部分失敗が他データを消さないよう配慮。
- テスト容易性のため、OpenAI 呼び出し関数はモジュール内で切り出されており、ユニットテストで patch しやすい構造になっている。

---

今後のリリースでは、strategy・execution・monitoring パッケージの具体的な売買ロジック・発注処理・監視機能の実装状況に応じて変更履歴を追加していきます。