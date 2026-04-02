# CHANGELOG

すべての変更は Keep a Changelog の規約に従って記載しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

なお、バージョンや日付はソース内の情報（`__version__` 等）および本ドキュメント作成日を元に設定しています。

## [Unreleased]

（現在のスナップショットに対する未リリースの差分はありません）

## [0.1.0] - 2026-04-02

初回リリース。本リリースでは日本株自動売買システム「KabuSys」のコア機能群を実装しています。主な追加点は以下の通りです。

### Added

- パッケージ基盤
  - パッケージエントリポイント `kabusys` を追加。バージョン `0.1.0` を `src/kabusys/__init__.py` に定義。
  - パッケージ公開 API として主要サブパッケージ（data, research, ai, monitoring, execution, strategy 等）を想定。

- 環境設定/ロード (`src/kabusys/config.py`)
  - .env ファイルや環境変数から設定値を自動読み込みする仕組みを実装。
  - プロジェクトルート検出機能（`.git` または `pyproject.toml` を探索）を導入し、CWD に依存しない自動読み込みを実現。
  - `.env` と `.env.local` の読み込み優先度を実装（OS 環境変数を保護する protected 機能）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化オプションを追加（テスト時の利便性向上）。
  - `.env` パーサーで `export KEY=val`、単/二重引用、インラインコメントなどに対応する堅牢なパース実装を追加。
  - 設定アクセス用 `Settings` クラスを提供（J-Quants / kabuAPI / Slack / DB パス / 監視閾値 / 環境種別など）。必須環境変数は `_require` を通じて明確にエラー化。
  - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（許容値チェック）を実装。

- AI モジュール（LLM を用いたニュース解析）
  - ニュースセンチメントスコアリング（`src/kabusys/ai/news_nlp.py`）
    - 指定したニュース時間ウィンドウの集約ロジック（日本時間の前日 15:00 〜 当日 08:30 相当）を実装（`calc_news_window`）。
    - raw_news + news_symbols から銘柄ごとに記事を結合して LLM にバッチ送信し、銘柄別スコアを ai_scores に書き込む `score_news` を実装。
    - バッチサイズ、1銘柄あたりの記事数/文字数上限、JSON モードの利用、レスポンスバリデーション、スコアの ±1.0 クリップ処理を導入。
    - OpenAI 呼び出しで 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他エラーはフェイルセーフにより個別チャンクをスキップして継続。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（`_call_openai_api` のモックを想定）。
    - DuckDB の `executemany` が空リストを受け付けないことを考慮した安全な DB 書き込みフロー（DELETE → INSERT、コード絞り込みで部分失敗耐性）。
  - 市場レジーム判定（`src/kabusys/ai/regime_detector.py`）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出する `score_regime` を実装。
    - prices_daily からの MA200 比率計算、raw_news からマクロキーワードで記事抽出、LLM によるマクロセンチメント評価（gpt-4o-mini を想定）を実装。
    - API エラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ設計。
    - スコア合成後は `market_regime` テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み、失敗時は ROLLBACK を試みて例外を上位に伝播。
    - LLM 呼び出しに対するリトライおよび 5xx 判定の実装（リトライ回数・バックオフ設定）。

- データ基盤（DuckDB ベース）
  - ETL パイプラインインターフェース（`src/kabusys/data/pipeline.py` / `src/kabusys/data/etl.py`）
    - ETL 実行結果を表す `ETLResult` データクラスを追加（取得/保存件数、品質問題リスト、エラーリスト等を含む）。品質問題の辞書化変換機能も持つ。
    - 差分更新・バックフィル・品質チェックを想定した設計方針を実装。
  - マーケットカレンダー管理（`src/kabusys/data/calendar_management.py`）
    - JPX カレンダーの夜間差分更新ジョブ（`calendar_update_job`）を実装。J-Quants クライアントからの取得→保存を行う。
    - カレンダーが一部しか無い場合でも一貫した振る舞いをする営業日判定ロジックを実装：`is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`。
    - DB 登録値を優先し、未登録は曜日（weekend）フォールバックする方針。探索上限 `_MAX_SEARCH_DAYS` 等で無限ループを防止。
    - バックフィル期間や先読み日数、健全性チェック（未来日付の異常検出）を実装。
  - jquants_client との連携を想定（差分取得・保存処理を jquants_client に委譲）。

- リサーチ / ファクター計算（`src/kabusys/research`）
  - ファクター計算モジュール（`factor_research.py`）
    - Momentum (1M/3M/6M リターン)、200日移動平均乖離、ATR 等の計算ロジックを DuckDB 上で SQL+Python により実装（`calc_momentum`, `calc_volatility`, `calc_value`）。
    - 欠損やデータ不足時の None 返却、200行未満などの条件処理を実装。
  - 特徴量探索モジュール（`feature_exploration.py`）
    - 将来リターン計算（`calc_forward_returns`）：複数ホライズンを一度に計算する効率的クエリを実装。
    - IC（Information Coefficient）計算（`calc_ic`）：スピアマンランク相関を実装。データ不足時は None を返す。
    - ランク変換ユーティリティ（`rank`）とファクター統計サマリー（`factor_summary`）を実装。
    - pandas 等に依存せず標準ライブラリのみで完結する実装方針。

### Changed

- 設計上の注意点・方針を明確化
  - 全ての時刻ロジックは datetime.today() / date.today() を直接参照しない設計でルックアヘッドバイアスを防止（関数は target_date を受け取る）。
  - LLM 連携は JSON Mode（厳密 JSON 出力）を前提にし、念のためレスポンス前後の余計な文字列をトリムして JSON を復元する堅牢化を行った。

### Fixed / Robustness

- DB トランザクションとエラーハンドリング強化
  - 書き込み失敗時に ROLLBACK を試み、さらに ROLLBACK 自体の失敗は警告ログに記録して例外を再送出する安全な実装。
  - DuckDB の executemany に空リストを渡さない防御ロジックを追加（互換性保持）。
- OpenAI API 周りの堅牢性
  - レスポンスパースエラー・レスポンスの型不整合・数値変換エラーなどは個別チャンクをスキップして全体処理を継続するフォールバック設計。
  - リトライ対象エラーの明確化と指数バックオフ実装。
- .env パーサーの堅牢化
  - コメントやクォート、エスケープシーケンス、export 構文に対応して誤認を減らす仕様。

### Security

- 環境変数の保護
  - OS 環境変数を protected として .env による上書きを防止する実装により、意図しない機密情報上書きを防止。

### Notes / Known limitations

- 実行時依存
  - OpenAI API クライアント（`openai`）および DuckDB が必須。
  - 実行には適切な環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）が必要。未設定時は `ValueError` を送出する箇所あり。
- 現フェーズでは一部指標（PBR・配当利回りなど）は未実装（`calc_value` に注記あり）。
- LLM 呼び出しはコストとレイテンシを伴うため、プロダクション運用時のバッチ設計やレート管理を要検討。
- `jquants_client` の具象実装は本スナップショット外で提供されることを前提。

---

（以降のリリースで、モジュール追加・API 変更・バグ修正・パフォーマンス改善・テストカバレッジ向上などの履歴を追記してください。）