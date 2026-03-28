# Changelog

すべての重要な変更をここに記載します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

現在のリリース方針: 0.1.0 を初期リリースとして記録しています。

[Unreleased]

---

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムのコア機能群を追加。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 環境設定 / ロード機能（kabusys.config）
  - プロジェクトルートを .git または pyproject.toml を基準に探索して .env/.env.local を自動読み込みする機能を追加（CWD に依存しない実装）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト時の利用を想定）。
  - .env パーサーを実装:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート、バックスラッシュエスケープに対応した値抽出。
    - コメント処理（クォート内は無視、クォート外はスペース直前の `#` をコメントとみなす等）。
  - `.env` 読み込み失敗時に警告を出す（読み込みの堅牢化）。
  - 必須環境変数取得用 `_require()` と Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス など設定プロパティを用意。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）。
    - `duckdb` / `sqlite` のデフォルトパス設定。

- AI (自然言語処理) モジュール（kabusys.ai）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）
    - 指定タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を計算するユーティリティを提供 (`calc_news_window`)。
    - raw_news / news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - バッチサイズ、記事数上限、文字数トリムなどトークン肥大化対策を実装。
    - OpenAI 呼び出しは JSON mode を利用し、レスポンスバリデーションを厳格化（results 配列、code と score の存在確認、数値の有限性チェック）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライを実装。失敗時は個別チャンクをスキップして処理継続（フェイルセーフ）。
    - DuckDB 互換性を考慮して、`executemany` に空リストを渡さないなどの対処を実装。
    - パブリック API: `score_news(conn, target_date, api_key=None)` を追加（取得した銘柄数を返す）。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能な設計（`_call_openai_api` を patch 可能）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - 日次で市場レジーム（'bull' / 'neutral' / 'bear'）を判定する `score_regime(conn, target_date, api_key=None)` を追加。
    - 判定ロジック:
      - ETF 1321 の直近200日終値から MA200 乖離率を算出（ルックアヘッド防止のため target_date 未満データのみ使用）。
      - マクロ経済ニュースタイトルを抽出し、LLM（gpt-4o-mini）でマクロセンチメントを評価。
      - 加重合成（MA 70% / マクロ 30%）、スコアをクリップしてラベル付与。
    - API の冗長性対策（リトライ・フェイルセーフ: API 失敗時は macro_sentiment=0.0）。
    - DB への書き込みは冪等に実施（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データ処理・ETL（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETL 実行結果を表す `ETLResult` データクラスを追加（品質チェック結果、各種取得/保存件数、エラーリストなどを含む）。
    - 差分取得・バックフィル・品質チェックの方針とユーティリティを実装（最小取得日、バックフィル日数、カレンダー先読みなど）。
    - DuckDB 上での最大日付取得やテーブル存在チェックなどのユーティリティを追加。
  - ETL の公開エントリポイント（kabusys.data.etl）として `ETLResult` を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days=...)` を追加。
    - 既存データの最終日チェック、バックフィル、健全性チェック（未来日付が過度に先の場合はスキップ）を実装。
    - 営業日判定ユーティリティ:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日）を使用する一貫した挙動。
      - 最大探索日数制限を設け無限ループを防止。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）を計算する `calc_momentum(conn, target_date)`。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算する `calc_volatility(conn, target_date)`。
    - Value: PER / ROE を計算する `calc_value(conn, target_date)`（raw_financials から最新財務データを取得して計算）。
    - 条件不十分な場合は None を返す設計（データ不足に対する堅牢化）。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）
    - 将来リターン計算 `calc_forward_returns(conn, target_date, horizons=None)` を追加（デフォルト horizons=[1,5,21]）。
    - IC（Information Coefficient）計算 `calc_ic(factor_records, forward_records, factor_col, return_col)`（スピアマンの順位相関）を実装。
    - 値をランクに変換する `rank(values)` と、ファクターの統計要約 `factor_summary(records, columns)` を提供。
    - 実装は標準ライブラリのみで、Pandas 等に依存しない設計。

- モジュール間のエクスポート整理
  - ai、research パッケージの __init__ で主要関数を明示的にエクスポート（テストと利用の利便性向上）。

### Changed
- ルックアヘッドバイアス対策を徹底
  - AI スコアリング・レジーム判定・ETL 等のコア関数で `datetime.today()` / `date.today()` を直接参照しない設計に統一。すべて呼び出し側から `target_date` を受け取る方式に統一し、過去データのみを参照する（安全側設計）。

- DuckDB 互換性向上
  - executemany に空リストを渡さないチェックを導入（DuckDB 0.10 系互換性のため）。

### Fixed
- OpenAI レスポンス処理の堅牢化
  - JSON mode を利用するが、稀に前後に余計なテキストが混入するケースを考慮して「最外の {} 抽出」等の復元処理を追加。パース失敗時は警告ログを出して該当チャンクをスキップする実装。
- API エラー取り扱いの明確化
  - OpenAI SDK の異なる例外型（APIError の status_code 存在/非存在）に対応し、5xx 系はリトライ、その他は即時フェイルセーフとする処理を明確化。

### Security
- 環境変数の保護
  - .env ファイル読み込み時に OS 環境変数キーを protected として扱い、`.env.local` の override が OS 環境変数を上書きしないよう保護。
  - 必須の外部 API キー（OpenAI 等）を未設定で呼び出すと明示的に ValueError を送出し安全性を担保。

### Notes / Implementation details
- OpenAI モデル: gpt-4o-mini を想定し JSON モードで呼び出す実装。
- API 呼び出し部はテスト時の差し替え（モック）を想定して分離している（`_call_openai_api` を patch 可能）。
- DB 書き込みは冪等性を重視（DELETE→INSERT や ON CONFLICT 相当の保存を前提）。
- 各モジュールは外部の発注 API や本番口座操作には一切アクセスしない設計（研究/分析と実行を分離）。

---

将来のリリースでは、発注実行モジュール、モニタリング、追加の品質チェックルール、その他 UX/運用改善（ログの構造化、メトリクス出力、CI テスト増強等）を予定しています。