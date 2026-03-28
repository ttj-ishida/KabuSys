CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
日付はリポジトリ内のコードや現行日付から推測しています。

Unreleased
----------

- ありません（初回リリースは 0.1.0 を参照）。

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ基盤を追加
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring。

- 環境変数 / 設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git / pyproject.toml 基準）から自動ロードする仕組みを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 行パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供し、J-Quants・kabu API・Slack・DB パス・実行環境（development/paper_trading/live）・ログレベルの取得とバリデーションを実装。
  - 必須環境変数未設定時は明示的な ValueError を送出。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを実装（calc_news_window）。
  - 1 銘柄あたりの記事数・文字数上限やバッチサイズ（最大 20 銘柄）などトークン肥大化対策を導入。
  - JSON Mode を利用したレスポンス検証と、応答パースのロバスト化（前後の余分なテキストから JSON を抽出する復元ロジック含む）。
  - API レート制限・ネットワーク断・タイムアウト・5xx の際に指数バックオフでリトライし、失敗はログ出力の上でフェイルセーフにフォールバック（部分失敗時に既存スコアを保護するため、書き込み時は対象コードのみ DELETE→INSERT）。
  - スコアは ±1.0 にクリップ、数値検証と未知コードの無視など堅牢なバリデーションを実装。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等的に保存する機能を実装。
  - LLM 呼び出しは独自のラッパ（JSON Mode、リトライ、エラーハンドリング）で実装し、API 失敗時は macro_sentiment=0.0 のフェイルセーフを採用。
  - ルックアヘッドバイアス対策（target_date 未満のデータのみを利用、datetime.today()/date.today() を直接参照しない）を徹底。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン用の ETLResult データクラスを公開（kabusys.data.etl / pipeline）。
  - 市場カレンダー管理（calendar_management）を実装: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day、および夜間バッチ更新 job（calendar_update_job）。
  - market_calendar が未取得の場合の曜日ベースのフォールバック、DB 登録値優先の一貫した判定ロジック、探索上限 (_MAX_SEARCH_DAYS) による安全対策を導入。
  - calendar_update_job は J-Quants から差分取得して冪等に保存し、バックフィル・健全性チェックを行う。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）を実装: Momentum（1M/3M/6M リターン、ma200 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比率）。
  - 特徴量探索ユーティリティ（feature_exploration）を実装: 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、rank（同順位の平均ランク処理）、統計サマリー（count/mean/std/min/max/median）。
  - 実装方針として DuckDB を直接クエリして標準ライブラリのみで処理（pandas 等非依存）、ルックアヘッド防止のため date 引数に依存する設計を採用。

Changed
- （初回リリースのため過去の変更はなし）  

Fixed
- （初回リリースのため過去の修正はなし）

Security
- OpenAI API キーを引数で注入可能にし、環境変数 OPENAI_API_KEY と併せて安全に扱えるように実装（明示的未設定時に ValueError を送出）。

Notes / 実装上の注記
- DuckDB をデータ層の主要ストレージとして想定。SQL 実行は DuckDB の互換性を考慮した実装（executemany 空リスト回避など）になっている。
- 多くの箇所で冪等保存（DELETE→INSERT、ON CONFLICT 相当）やトランザクション（BEGIN/COMMIT/ROLLBACK）を採用し、部分失敗時のデータ保護に配慮。
- LLM 呼び出しは JSON Mode を利用しつつ、パース失敗時の復元や堅牢なエラーハンドリング（非致命的フォールバック）を組み込んでいるため、本番環境での安定運用を意識した実装となっている。
- 日時・ウィンドウ計算は JST/UTC を明確に扱い、ルックアヘッドバイアスを避ける設計。

今後の予定（想定）
- strategy / execution / monitoring 周りの実装公開（現状はパッケージエクスポートのみ）。
- J-Quants / kabu ステーション向けクライアントや保存処理の拡充・テストケース追加。
- 追加の品質チェックルールとモニタリング通知（Slack 連携等）の強化。