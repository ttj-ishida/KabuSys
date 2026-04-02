# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従って管理しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（現時点なし）

## [0.1.0] - 2026-04-02
初回リリース。以下の主要機能とモジュールを追加しました。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - サブパッケージ公開: data, strategy, execution, monitoring。

- 設定・環境変数管理 (kabusys.config)
  - プロジェクトルートを .git または pyproject.toml から自動検出し、.env / .env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env パーサ実装（export 形式、クォート付き値、インラインコメントの扱い、保護キー上書き制御）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベース / 監視 / ログレベル等の環境設定をプロパティで取得（未設定時の検証・例外処理あり）。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースセンチメントスコアリング（news_nlp.score_news）
    - 指定のニュース時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事収集。
    - news_symbols と結合して銘柄ごとに記事を集約し、1銘柄あたりの文字数・記事数をトリム。
    - OpenAI（gpt-4o-mini）の JSON mode を用いたバッチ評価（最大バッチサイズ、リトライ・指数バックオフ、レスポンス検証、スコアの±1クリップ）。
    - DuckDB の ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。部分失敗時に他銘柄の既存スコアを保護する実装。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に実装。
  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily market_regime を判定（'bull' / 'neutral' / 'bear'）。
    - マクロキーワードで raw_news をフィルタ、OpenAI によりマクロセンチメントを算出（フェイルセーフ: API失敗時は 0.0）。
    - DuckDB の market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しはリトライ、エラー種別ごとの処理やログ出力を実装。

- データ基盤 (kabusys.data)
  - カレンダー管理（data.calendar_management）
    - market_calendar テーブルを基に営業日判定、次/前営業日取得、期間内営業日取得、SQ日判定のユーティリティを提供。
    - market_calendar 未取得時は曜日ベースでフォールバックする設計。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する夜間バッチ calendar_update_job を実装（バックフィル・健全性チェックあり）。
  - ETL パイプライン基盤（data.pipeline / data.etl）
    - ETLResult データクラスを公開（取得・保存レコード数、品質チェック結果、エラー一覧等の構造化）。
    - 差分更新・バックフィル・品質チェック統合のためのユーティリティ（jquants_client / quality モジュールとの連携想定）。
    - DuckDB 互換性を考慮した実装（executemany の空リスト回避等）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュール
    - calc_momentum：1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時の扱い明示）。
    - calc_volatility：20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播制御等）。
    - calc_value：raw_financials から直近財務を取得して PER・ROE を計算（EPSが0/欠損時の扱い）。
  - feature_exploration モジュール
    - calc_forward_returns：指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する効率的クエリ。
    - calc_ic：ファクター値と将来リターンの Spearman ランク相関（IC）を計算（十分なレコード数がない場合は None）。
    - rank：同順位扱いは平均ランクで処理するランク関数（浮動小数の丸め対策あり）。
    - factor_summary：各カラムの count/mean/std/min/max/median を計算する統計サマリ。

### 改善（設計・実装上の配慮）
- ルックアヘッドバイアス回避の徹底（datetime.today()/date.today() を直接参照しない、クエリで target_date 未満/以前条件を明示）。
- OpenAI 呼び出しのフェイルセーフ設計（リトライ、5xx とそれ以外の扱い分離、JSON パース失敗時の安全退避）。
- DuckDB に対する互換性・制約を考慮（空の executemany 回避、日付値の変換ユーティリティ等）。
- テスト容易性のため外部 API 呼び出し点を差し替え可能に実装（モック化を容易にする設計）。

### 既知の制約・注意点
- OpenAI API キーが未設定の場合、news_nlp.score_news / regime_detector.score_regime は ValueError を送出する（api_key 引数か環境変数 OPENAI_API_KEY を必要とする）。
- 一部機能は J-Quants / kabuステーション / Slack 等の外部サービスと連携する想定で、実行には適切な環境変数と DB スキーマ（DuckDB の各テーブル）が必要。
- calendar_update_job や ETL 関連は外部 jquants_client の実装に依存する（fetch/save 関数の例外はキャッチして 0 を返す設計）。

## 今後の予定（例）
- strategy / execution / monitoring サブパッケージの具体的な戦略実装と注文実行ロジックの追加。
- 品質チェック（data.quality）の実装強化と ETL の自動通知 / アラート機能。
- テストカバレッジの拡充および CI ワークフローの整備。

---

（注）本CHANGELOGは現行コードベースから推測して作成しています。実際のリリースノート作成時は、コミット履歴やリリース方針に合わせて調整してください。