# Changelog

すべての注目すべき変更は Keep a Changelog の形式に従って記録しています。  
慣例: 重大度の高い変更は Breaking Changes / 注意事項として明記します。

※ 以下は提供されたコードベースの実装内容から推測して作成した初回リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティ群の基本実装を追加。

### Added
- パッケージのエントリポイントを追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - 公開モジュール: data, strategy, execution, monitoring（__all__ に含む）

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装
    - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動読み込みの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - .env パーサ実装（クォート、エスケープ、コメント、export KEY= 形式に対応）
  - protected（既存 OS 環境変数）を上書きしない読み込みロジック
  - Settings クラスを追加（プロパティ経由で設定値を取得）
    - J-Quants / kabuステーション / Slack / DB パス / システム設定 等のプロパティ
    - env, log_level に対する値検証（許容値チェック）
    - duckdb_path / sqlite_path は Path として正規化

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄につき最大記事数 / 最大文字数でトリム
    - JSON Mode の出力検証と堅牢なパース処理（前後ノイズを許容する復元ロジック）
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ
    - スコアを ±1.0 にクリップ、部分失敗時に既存スコアを保護するため code を絞って DELETE → INSERT
    - テスト容易性のため _call_openai_api を差し替え可能に設計
    - calc_news_window ユーティリティ（ニュース収集ウィンドウ: 前日15:00JST〜当日08:30JST の UTC 換算）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースセンチメント（重み 30%）を組み合わせて日次レジーム判定
    - OpenAI（gpt-4o-mini）によるマクロセンチメント評価（上位 API 呼び出しと独立した _call_openai_api 実装）
    - DB（DuckDB）の prices_daily / raw_news / market_regime を参照・更新。冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - API 失敗時のフェイルセーフ（macro_sentiment=0.0）とリトライ制御

- Data モジュール（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を基にした営業日判定ユーティリティ群を提供
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベース（週末を非営業日）でフォールバックする一貫したロジック
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィル・健全性チェックあり）
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開（ETL 実行結果の構造化）
    - 差分取得・保存・品質チェックのためのユーティリティ（設計に則ったエラーハンドリングと部分書き込み保護）
  - etl.py は pipeline.ETLResult を再エクスポート

- Research（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム、ボラティリティ、バリュー等の定量ファクターを DuckDB SQL で計算
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日MA乖離）
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率
    - calc_value: PER / ROE（raw_financials と prices_daily を結合）
    - 実装は DB read-only、外部 API 不使用（研究用）
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を使用）
    - calc_ic: スピアマンランク相関（ランク化は ties を平均ランクで処理）
    - rank, factor_summary: ランク付け・統計サマリーのユーティリティ（外部依存なし）

### Changed
- （初回公開につき該当なし）

### Fixed
- （初回公開につき該当なし）

### Security
- OpenAI API キーは引数で注入可能か環境変数 `OPENAI_API_KEY` を参照する。キーの取り扱いは利用者側で管理すること。

### Notes / Design Decisions / Known behaviors
- ルックアヘッドバイアス回避:
  - AI スコア・レジーム判定・ニュースウィンドウ・ファクター計算はいずれも datetime.today() / date.today() を内部で参照しない実装方針（呼び出し側が target_date を明示）。
- フェイルセーフ:
  - OpenAI API の不可用時は例外を投げずにフェイルセーフ値（例: macro_sentiment=0.0、スコア未取得のスキップ）で継続する設計。DB 書き込み失敗時はトランザクションをロールバックして上位へ例外を伝搬。
- DuckDB 互換性:
  - executemany に空リストを渡すと失敗する環境（例: DuckDB 0.10）を考慮して、空チェックを行った上で executemany を呼ぶ。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定した JSON Mode を利用。レスポンス検証および前後ノイズ処理を実装。
  - API 呼び出しのラップ関数（_call_openai_api）をテストで差し替え可能。
- .env パーサ:
  - シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱い、export プレフィックス に対応。
- DB 書き込みの冪等性:
  - market_regime / ai_scores などは対象コード/日付で既存行を削除してから挿入する方式で部分失敗時に他データを守る実装。

### Dependencies（実装から推測）
- openai (OpenAI SDK を利用した chat completions 呼び出し)
- duckdb

---

今後の改善案（推奨）
- 単体テスト・統合テストの充実（OpenAI 呼び出しのモック・DuckDB のテストフィクスチャ）
- ロギングの標準化と構造化ログ出力フォーマットの採用
- レート制限やコスト最適化のためのバッチ戦略改善（同一日における呼び出し同梱など）
- ai_scores / market_regime に対するスキーマ定義とマイグレーションスクリプトのドキュメント化

（以上）