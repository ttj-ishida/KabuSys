KEEP A CHANGELOG
=================

すべての重要なリリース変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

履歴
----

### 0.1.0 - 2026-03-31

Added
- 初回公開リリース: 日本株自動売買支援ライブラリ "kabusys" を追加。
  - パッケージ構成（主要モジュール）:
    - kabusys.config: 環境変数 / .env 管理と Settings クラスを提供
      - プロジェクトルート自動検出（.git または pyproject.toml ベース）により .env/.env.local を自動ロード
      - .env パーサはコメント行・export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープを考慮
      - 環境変数の保護（OS 環境変数を上書きしない挙動）をサポート
      - Settings により J-Quants / kabu API / Slack / DB /監視閾値 / 実行環境（development/paper_trading/live）等のプロパティとバリデーションを提供
    - kabusys.ai.news_nlp: ニュースを OpenAI（gpt-4o-mini）でバッチセンチメント解析し ai_scores テーブルへ書き込む機能
      - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST 相当の UTC 範囲）
      - 銘柄ごとに記事を集約（記事数・文字数のトリム）
      - バッチ送信（最大 20 銘柄/チャンク）、再試行（429/ネットワーク/5xx に対する指数バックオフ）
      - レスポンスの厳密なバリデーションとスコア ±1.0 のクリップ
      - 部分失敗に備えた部分置換（DELETE → INSERT）による冪等書き込み
      - テスト用フック: OpenAI 呼び出しを patch で差し替え可能
    - kabusys.ai.regime_detector: ETF(1321) の 200日移動平均乖離とニュースセンチメントを合成して日次市場レジーム判定を行う
      - ma200_ratio の計算、マクロキーワード抽出、LLM によるマクロセンチメント評価（gpt-4o-mini）
      - 合成スコアの閾値判定（bull/neutral/bear）と market_regime テーブルへの冪等書き込み
      - API エラー時のフェイルセーフ（macro_sentiment=0.0）・リトライロジックを実装
      - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみを使用、date.today() を参照しない）
    - kabusys.research:
      - factor_research.calc_momentum / calc_volatility / calc_value: DuckDB 上の prices_daily / raw_financials を用いたファクター計算
        - Momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）
        - Volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率
        - Value: PER, ROE（最新報告ベース）
      - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank: 将来リターンとファクターの統計解析ユーティリティ
        - forward returns: リードウィンドウで複数ホライズンを一括取得、入力バリデーションあり
        - calc_ic: スピアマン ρ（ランク相関）を実装、最小サンプル条件を設置
        - factor_summary: 基本統計量（count, mean, std, min, max, median）
      - research パッケージは一部ユーティリティを再エクスポート（例: zscore_normalize）
    - kabusys.data:
      - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
        - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供
        - market_calendar データが無い場合は曜日ベースでフォールバック（土日非営業）
        - 夜間バッチ job (calendar_update_job): J-Quants から差分取得・バックフィル・冪等保存
        - 安全性チェック（未来日付の異常検出 / 最大探索日数制限）
      - pipeline / etl: ETL 実行用型（ETLResult）とパイプライン設計（差分取得・品質チェック・保存）インターフェース
        - ETLResult により取得/保存件数・品質問題・エラーを構造化して返す
      - etl モジュールは pipeline.ETLResult を再エクスポート
    - パッケージ全体:
      - DuckDB を主要な分析・データ格納レイヤとして想定
      - OpenAI API 呼び出しでの JSON Mode を用いた入出力（JSON レスポンスの厳密検証）
      - API キー注入（api_key 引数 or 環境変数 OPENAI_API_KEY）に対応しテスト性を向上

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Implementation details / Limitations
- OpenAI API
  - OpenAI の呼び出しは gpt-4o-mini を想定、レスポンスパース失敗や API エラーはログ出力の上フォールバック（スコア0.0 やスキップ）する設計。
  - テストでの安定化のため、内部の _call_openai_api を patch して差し替え可能。
- ルックアヘッドバイアス対策
  - すべての時系列・ウィンドウ計算は target_date を明示的に受け取り、date.today()/datetime.today() を直接参照しない実装方針を採用。
- データベース書き込み
  - ai_scores や market_regime への書き込みは部分置換・トランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。
  - DuckDB の executemany の制約（空リスト不可）に対応したガードを実装。
- カレンダー
  - market_calendar のデータが欠損している場合は曜日ベースでのフォールバックを行うが、DB にある値が優先される（登録済日の休日を正しく扱うため）。
- 設定読み込み
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用途）。
  - .env 読み込み時、既存 OS 環境変数はデフォルトで保護される（.env.local は override=True で上書き可能だが OS 環境変数は保護される）。
- 未実装 / 将来的な拡張
  - research の一部（PBR・配当利回り等の指標）は今後追加予定。
  - 実行・監視（monitoring）モジュールはパッケージ __all__ に含まれるが、本リリースでは監視関連の詳細な実装は限定的（コードベースに応じた記述）。

Authors / Contributors
- コードベースから判断した主要実装内容を記載（コミットログが無いため個別コントリビュータ名は未記載）。

ライセンス
- この changelog はコードベースの内容を基に推測して作成しています。実際のリリースノートはコミット履歴やリリース管理に合わせて調整してください。