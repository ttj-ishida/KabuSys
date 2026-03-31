# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムのコア機能群を実装しました（データ ETL、マーケットカレンダー、リサーチ/ファクター計算、ニュース NLP、レジーム判定、設定管理など）。

### Added
- パッケージ基盤
  - パッケージ名: `kabusys`
  - バージョン: `0.1.0`
  - 公開 API: data, strategy, execution, monitoring を __all__ として定義。

- 設定管理
  - `kabusys.config.Settings` クラスを実装。
    - 環境変数から各種設定を取得（J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベル 等）。
    - 必須変数取得時のエラー処理 (`_require`)。
  - `.env` / `.env.local` 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - OS 環境変数の上書きを保護する protected 機構。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - `.env` パーサーは quoted 値（エスケープ対応）や `export KEY=val` 形式、行内コメント処理に対応。

- AI（ニュース NLP / レジーム判定）
  - `kabusys.ai.news_nlp.score_news` を実装。
    - 指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）における raw_news を銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを評価して `ai_scores` テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄）・記事数/文字数トリム・レスポンス検証（JSON 抽出、results の検証）を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する再試行（指数バックオフ）を実装。
    - API 失敗時はスキップして継続するフェイルセーフ挙動。
    - DuckDB の executemany の制約（空リスト不可）を考慮した安全な DB 書き込み。
  - `kabusys.ai.regime_detector.score_regime` を実装。
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロセンチメント（OpenAI、30%）を合成して市場レジーム（bull / neutral / bear）を算出し `market_regime` テーブルへ冪等書き込みを行う。
    - マクロニュース抽出、OpenAI 呼び出し、リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
  - OpenAI 呼び出しはモジュールごとに独立したプライベート関数（テスト時に差し替え可能）。

- データ / ETL / カレンダー
  - `kabusys.data.pipeline.ETLResult` を実装（ETL 実行結果の集約・シリアライズ）。
  - `kabusys.data.etl` で ETLResult を再エクスポート。
  - `kabusys.data.calendar_management` を実装。
    - market_calendar テーブルに基づく営業日判定 API（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を実装。
    - JPX カレンダーを J-Quants から差分取得して更新する `calendar_update_job`（バックフィル・健全性チェック・冪等保存）を追加。
    - カレンダー未取得時の曜日ベースフォールバック（週末除外）や DB データがまばらな場合でも一貫した判定を行う設計。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`
    - `calc_momentum`: 1M/3M/6M リターン、200 日 MA 乖離などを算出。
    - `calc_volatility`: 20 日 ATR、相対 ATR、平均売買代金、出来高比率などを算出。
    - `calc_value`: PER（EPS に基づく）、ROE の算出（raw_financials を利用）。
    - DuckDB ベースの SQL 実装により外部 API に依存しない。
  - `kabusys.research.feature_exploration`
    - `calc_forward_returns`: 将来リターン（任意ホライズン）を一度のクエリで取得可能。
    - `calc_ic`: スピアマンランク相関（IC）の実装（結合・欠損除外・最小レコード数チェック）。
    - `rank`: 同順位の平均ランク処理を含むランク化ユーティリティ。
    - `factor_summary`: count/mean/std/min/max/median を計算する統計サマリー。
  - `kabusys.research.__init__` で主要関数を再エクスポート。

### Changed
- 設計上の重要ポイント（ドキュメント化・実装反映）
  - ルックアヘッドバイアス防止のため、どのモジュールも内部で datetime.today() / date.today() を不必要に参照しない設計を採用。target_date を明示的に渡す API を中心に実装。
  - DuckDB 互換性を考慮した実装（空パラメータでの executemany 回避、日付型変換ユーティリティ等）。
  - OpenAI 呼び出しについては 5xx/RateLimit/ネットワーク障害での再試行ロジックを標準実装し、非 5xx エラーやレスポンスパースエラーの場合は安全にフォールバックする挙動を採用。

### Fixed / Robustness
- 環境変数読み込みの堅牢化
  - .env パーサーが引用符付き文字列内のバックスラッシュエスケープを適切に扱うよう改善。
  - コメントの扱い、`export KEY=val` 形式への対応、ファイル読み込み失敗時の警告出力を追加。
  - 自動ロード時に OS 環境変数を保護（protected set）することで意図しない上書きを防止。
- OpenAI 統合の堅牢化
  - レスポンス JSON の前後余計テキストを復元してパースする処理を追加（JSON mode でも副次テキストが混入する場合への耐性）。
  - レスポンス検証で未知銘柄コードを無視することで LLM の逸脱出力が部分的にあっても既存データを保護。
  - API エラー発生時に WARN ログを出し、致命的な例外ではなくフォールバック（スコア 0.0 やスキップ）する実装。
- DB 書き込みの原子性・冪等性
  - market_regime / ai_scores 等への書き込みは BEGIN/DELETE/INSERT/COMMIT のパターンで冪等性を確保。
  - 失敗時は ROLLBACK を試み、ROLLBACK 失敗は警告ログ化して上位へ例外を伝播。

### Documentation / Tests（テストしやすさ）
- テスト容易性のため、OpenAI 呼び出し部分を内部関数化して unittest.mock.patch により差し替え可能に実装（news_nlp._call_openai_api, regime_detector._call_openai_api）。
- 各モジュールに処理フロー・設計方針・注意点をモジュールドクストリングとして明記。

### Known limitations
- 一部モジュール（strategy / execution / monitoring）は __all__ に含まれるが、このリリース内の実装コードは今回の公開範囲（データ・リサーチ・AI・設定）に重点を置いています。
- OpenAI 依存部分は API キーの設定が必須（api_key 引数または環境変数 OPENAI_API_KEY）。API の仕様変化に伴う調整が必要になる可能性あり。

---

（注）上記はソースコードから推測した初期リリースの変更履歴です。各機能の詳細や使用法は該当モジュールのドキュメント・コード内 docstring を参照してください。