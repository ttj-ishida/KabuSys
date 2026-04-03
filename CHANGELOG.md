Keep a Changelog 準拠 — CHANGELOG.md
=================================

すべての重要な変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に従い、セマンティックバージョニングを使用します。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-03
-------------------

初回公開リリース。以下の主要機能と実装方針を含みます。

追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0、公開モジュール: data, strategy, execution, monitoring）。
- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）。
  - .env パーサを堅牢化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなし時のコメント判定などに対応。
    - ファイル読み込み失敗時に警告を発行し続行。
  - Settings クラスを提供（J-Quants / kabuステーション / LINE / DBパス / 監視閾値 / 環境種別 / ログレベル等をプロパティ経由で取得）。未設定の必須値は明示的な例外を投げる。
  - 環境変数の保護（OS 環境変数を protected set として .env.local が上書きする際に考慮）。
- データ関連 (kabusys.data)
  - ETL パイプライン（pipeline.ETLResult の公開）: ETL 実行結果を表す dataclass を実装（取得件数、保存件数、品質問題一覧、エラー一覧等を包括）。
  - カレンダー管理（calendar_management）:
    - JPX マーケットカレンダー管理ロジック（market_calendar テーブルの参照／更新、営業日判定、前後営業日の計算、期間内営業日取得、SQ判定）。
    - データがない場合の曜日ベース（週末）フォールバックを採用し、DB 登録ありの場合は DB 値優先で一貫性を保つ実装。
    - 夜間バッチジョブ calendar_update_job を実装。J-Quants からの差分取得、バックフィル（直近数日）、健全性チェック（将来日付閾値）を含む。
  - ETL モジュール（data.pipeline）:
    - 差分取得・保存・品質チェックを想定した ETLResult クラスを実装。品質チェックの重大度判定プロパティを提供。
    - DuckDB を利用したテーブル存在チェックや最大日付取得などのユーティリティを用意。
- 研究・ファクター (kabusys.research)
  - ファクター計算（research.factor_research）:
    - モメンタム: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算する calc_momentum を実装。データ不足時の None 扱いを明示。
    - ボラティリティ／流動性: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算する calc_volatility を実装。NULL / データ不足の取扱を考慮。
    - バリュー: raw_financials から最新の財務データを取得して PER / ROE を計算する calc_value を実装。EPS が 0/NULL の場合 PER は None。
    - 設計上、prices_daily / raw_financials の参照のみで、実際の発注等には影響しない分離を明示。
  - 特徴量探索（research.feature_exploration）:
    - 将来リターン計算 calc_forward_returns（指定ホライズンの将来終値リターン）。ホライズン入力のバリデーションあり。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関）、rank ユーティリティ（同順位は平均ランク）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - 実装は外部ライブラリに依存せず標準ライブラリ＋DuckDB を使用。
- AI（自然言語処理）機能 (kabusys.ai)
  - ニュース NLP スコアリング（news_nlp.score_news）:
    - 指定日のニュースウィンドウ（前日15:00 JST〜当日08:30 JST に対応する UTC 時間）を集計し、銘柄ごとに最大記事数・文字数で整形して OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、JSON Mode 出力のバリデーション、応答パース、スコアの ±1.0 クリップ、部分書込み（対象コードに限定した DELETE → INSERT）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフ retry を実装。API 失敗はログ出力してフェイルセーフにより継続（例外を投げずスキップ）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
  - 市場レジーム判定（ai.regime_detector.score_regime）:
    - ETF 1321（日経225連動型）の直近200日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を統合して日次の market_regime テーブルへ冪等書込。
    - マクロニュースはニュース NLP からウィンドウ算出（calc_news_window）を利用して抽出し、OpenAI に JSON 出力を要求して数値スコア化。API エラー時のフォールバック（macro_sentiment=0.0）を明示。
    - レジームスコアは clip(-1,1) 後に閾値で bull/neutral/bear を判定。
    - DuckDB を用いたトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等保存。書込失敗時は ROLLBACK を試み、失敗メッセージはログに記録。
    - OpenAI API 呼び出しのリトライとエラー分類（RateLimitError/APIConnectionError/APITimeoutError/APIError）の扱いを実装。
- テスト／安全設計上の配慮（全体）
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を不要に参照しない設計（全て target_date を明示的に渡す）。
  - DuckDB を主なストレージとして利用し、executemany の空リスト回避など DuckDB の挙動を考慮した実装。
  - 外部 API 呼び出しの失敗は基本的にスキップ・フェイルセーフで扱い、システム全体の安定性を優先。

変更 (Changed)
- なし（初回リリースのため）

修正 (Fixed)
- なし（初回リリースのため）

削除 (Removed)
- なし

既知の制約・注意点
- OpenAI API は gpt-4o-mini を想定して実装。API キーは引数経由または環境変数 OPENAI_API_KEY を使用する（未設定時は ValueError を送出）。
- news_nlp / regime_detector は JSON 出力を厳密に要求するが、実環境では LLM の応答に揺らぎがあるためパース回復処理（前後テキストから最外の {} を抽出）を実装している。
- DuckDB のバージョン依存の振る舞い（executemany 空リスト不可等）に注意。
- calendar_update_job は J-Quants クライアント実装（jquants_client）に依存する。API 呼び出し・保存処理が失敗した場合は 0 を返している。

付記
- 各モジュールは「外部への副作用を最小化する」「テスト容易性」「ルックアヘッド回避（データリーク防止）」を基本方針として設計されています。今後のリリースでは strategy / execution / monitoring 周りの実装を充実させ、より運用向けの監視・発注ロジックを追加予定です。