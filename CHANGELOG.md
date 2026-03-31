# Changelog

すべての notable な変更点はこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠しています。  
リリース日の日付はコードベースの提出日（本ファイル作成日）を使用しています。

## [Unreleased]

（現時点では未リリースの変更はありません。初回リリースは以下を参照してください。）

---

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買/データ基盤のコア機能群を実装しました。主に以下のコンポーネントを含みます。

### 追加（Added）
- パッケージ基盤
  - pakage メタ情報: `src/kabusys/__init__.py` に v0.1.0 を設定。
  - 公開サブモジュール: data, strategy, execution, monitoring（__all__ 定義）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定をロードする自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応（テスト用途）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない動作。
  - .env パーサ実装（コメント、export プレフィックス、クォート／エスケープ処理に対応）。
  - 必須設定取得用ユーティリティ _require と Settings クラスを提供。
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 環境種別 / ログレベル 等のプロパティを用意。
    - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini）へのバッチ送信（最大 20 銘柄／回）、JSON mode を用いた厳密なレスポンス処理。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを実装。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code/score の検証、スコアのクリップ）。
    - DuckDB の ai_scores テーブルへ冪等的に書き込むロジック（DELETE → INSERT、部分失敗時に既存データ保護）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
    - calc_news_window(t) を提供（日本時間の前日 15:00 ～ 当日 08:30 を UTC で扱う）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio とニュースタイトルを取得。
    - OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを取得。API エラー時はフェイルセーフで macro_sentiment=0.0。
    - レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。

- データプラットフォーム（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを基にした営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時は曜日ベース（平日のみ営業）でフォールバック。
    - JPX カレンダーを J-Quants API から差分取得して更新する夜間バッチ job（calendar_update_job）を実装（バックフィル、健全性チェック、冪等保存）。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL 実行結果を表す ETLResult データクラスを追加（品質チェック結果・エラー情報などを保持、dict 出力対応）。
    - 差分更新・保存・品質チェックの設計方針を組み込んだパイプライン基盤（J-Quants クライアント経由の差分取得、保存の idempotent 実装想定）。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）等の計算関数を実装。
    - DuckDB を用いた SQL ベースの計算。結果は (date, code) をキーとした dict のリストで返却。
    - データ不足時の None ハンドリング、ログ出力。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、可変ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算（Spearman ρ）とランク化ユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）。

### 変更（Changed）
- （初回リリースのため該当なし）

### 修正（Fixed）
- （初回リリースのため該当なし）

### セキュリティ（Security）
- 環境変数管理に関する注意:
  - J-Quants / OpenAI / Kabu API / Slack トークン等の機密情報は環境変数経由で取得（Settings クラスの必須プロパティでチェック）。
  - .env 自動ロード時、既存の OS 環境変数は保護される（.env.local による上書きは可能だが OS 環境変数は protected）。
  - 自動ロードを完全に無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト環境向け）。
- OpenAI 呼び出しは外部 API であるため、API キーの管理に注意。コード側では API 呼び出しの失敗をフェイルセーフで処理する設計（例: macro_sentiment=0.0）。

### 注意・設計上のポイント（Notes）
- ルックアヘッドバイアス防止:
  - AI モジュール（news_nlp, regime_detector）および研究モジュールは datetime.today()/date.today() を直接参照しない設計。全て target_date を明示的に渡して評価することで将来情報の漏出を防止。
  - DB クエリは target_date 未満／排他条件などを明示的に扱っている。
- 冪等性とトランザクション:
  - market_regime / ai_scores 等への書き込みは冪等（DELETE→INSERT 等）かつ BEGIN/COMMIT/ROLLBACK を用いた処理。ROLLBACK の失敗ログも捕捉。
- API 呼び出しの堅牢性:
  - OpenAI 呼び出しは 429/ネットワーク/タイムアウト/5xx に対するリトライ（指数バックオフ）を実装。致命的でない失敗はスキップして処理継続（フェイルセーフ）。
  - レスポンスの JSON パースやスキーマ不整合に対してはログを出し空結果を返却することで上位処理の安定を確保。
- DuckDB 互換性配慮:
  - executemany に空リストを渡すと失敗するバージョンがあるため、空チェックを行ってから実行する実装（ai_scores への書き込み等）。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数（_call_openai_api）をパッチ可能に実装しており、単体テストで API をモックしやすい設計。

### 既知の制限（Known issues / Limitations）
- 一部 API クライアント（J-Quants / Kabu）が仮想的に参照される設計で、実動作には外部サービスとテーブルスキーマ（DuckDB）準備が必要。
- Strategy / execution / monitoring の具体的な実行・注文ロジックは本リリースでは含まれていない（パッケージの公開インターフェースには含めているが実装は別途）。

---

履歴管理ポリシー:
- セマンティックバージョニング（MAJOR.MINOR.PATCH）を想定。
- 重大な後方互換性破壊は MAJOR を増やす。

（終）