# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog 準拠の形式で記載しています。

フォーマット:
- Unreleased: 今後の変更（空欄または作業中の項目）
- 各リリースは日付付きで記載し、カテゴリ（Added / Changed / Fixed / Deprecated / Security）ごとに分けます。

## [Unreleased]

---

## [0.1.0] - 2026-04-02

初期リリース。日本株自動売買／データ基盤／リサーチ用の基盤的モジュール群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化、バージョン番号を `__version__ = "0.1.0"` に設定。
  - 公開 API（__all__）に data, strategy, execution, monitoring を追加。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - `.env` / `.env.local` の読み込み優先度を実装（OS 環境変数を保護する protected 機能）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動読み込み無効化オプションを提供（テスト用）。
  - 複雑な .env パース処理対応（export プレフィックス、クォート内エスケープ、インラインコメント検出など）。
  - `Settings` クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム環境（development/paper_trading/live）などの設定プロパティを提供。
  - 設定値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須変数チェック `_require` を実装。

- AI モジュール (`kabusys.ai`)
  - `news_nlp.score_news`
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチサイズ・トークン肥大化対策（最大記事数／最大文字数制限）。
    - JSON Mode を用いたレスポンスバリデーション（結果抽出・スコアの ±1.0 クリップ）。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - DuckDB との冪等書き込み（DELETE → INSERT）、部分失敗時に既存スコアを保護する設計。
    - 単体テストのために OpenAI 呼び出しを差し替え可能（パッチ用フック）。
    - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を参照しない設計。
  - `regime_detector.score_regime`
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - raw_news からマクロキーワードでフィルタした記事を抽出し、LLM によりマクロセンチメントを取得。
    - API エラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ実装。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出しのリトライ・例外ハンドリングを実装。

- データ基盤 (`kabusys.data`)
  - ETL 基盤
    - `pipeline.ETLResult` データクラスを公開（取得件数、保存件数、品質問題、エラー集約、has_errors/has_quality_errors など）。
    - 差分取得・バックフィル・品質チェックを想定した設計方針を実装。
  - カレンダー管理 (`calendar_management`)
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants クライアント経由で差分取得→保存）。
    - 営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB にデータがない場合の曜日ベースのフォールバック、DB 値優先の一貫した挙動、最大探索日数の安全策を実装。
    - バックフィル・健全性チェック（future date の過大値検出）を実装。
  - jquants_client（参照用）との連携を想定。

- リサーチ / ファクター計算 (`kabusys.research`)
  - `factor_research`
    - Momentum, Value, Volatility, Liquidity などの定量ファクター計算関数を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m、200日 MA 乖離（データ不足時の None 処理）。
      - calc_volatility: 20日 ATR・相対 ATR・平均売買代金・出来高比など（true_range の NULL 伝播制御）。
      - calc_value: raw_financials と株価を組み合わせて PER/ROE を算出。
    - DuckDB ベースの SQL 実装で外部 API へアクセスしない安全設計。
  - `feature_exploration`
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得する SQL 実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（データ不足時は None）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
    - rank: 同順位は平均ランク化するランク関数（丸め処理で浮動小数の誤差を調整）。
    - pandas 等の外部ライブラリに依存しない純標準ライブラリ実装。

- 運用／監視設定
  - Settings に監視用閾値プロパティ（cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct）や pid_file_path を実装。
  - ログレベル設定検証（LOG_LEVEL）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数の取り扱いで OS 環境変数を保護する protected キーセットを導入。既存の OS 環境変数は .env によって上書きされないよう設計。

### Notes / Implementation details（重要な設計・制約）
- DuckDB 0.10 の挙動に合わせた実装上の注意：
  - executemany に空リストを渡さないチェックを行い互換性を保っている。
  - SQL バインドでリスト型の挙動が不安定な場合は個別 DELETE を executemany で実行する方式を採用。
- LLM 呼び出しに関して:
  - JSON Mode を利用し厳密な JSON 出力を期待するが、万一前後に余計なテキストが混ざる場合の復元ロジックを実装。
  - テスト容易性のため _call_openai_api をモジュールごとに差し替え可能にしている（モジュール間でプライベート関数を共有しない設計）。
- ルックアヘッドバイアス対策:
  - AI モジュール、Research モジュールなどで date.today()/datetime.today() を直接参照せず、呼び出し側から target_date を指定する設計。
- フェイルセーフ:
  - OpenAI API や外部 API の失敗時は例外をそのまま投げず、ログ出力のうえ安全側の既定値（例: macro_sentiment=0.0、スコアスキップ）で継続する箇所がある。

---

（今後のリリースでは、変更点をこのファイルに追記してください。）