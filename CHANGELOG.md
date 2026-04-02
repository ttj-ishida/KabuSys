Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは "Keep a Changelog" の慣例に従い、セマンティックバージョニングを使用します。

Unreleased
----------

注: 開発途中の既知の注意点・未実装箇所を記載しています（次回リリースで対応予定）。

- Known issues / TODO
  - data.pipeline._get_max_date の実装が途中で終了している断片が存在します（コード末尾に不完全な return がある）。ETL の一部ユーティリティで正しい最大日付取得が期待できないため、修正・追加テストが必要です。
  - OpenAI API 呼び出し周りはテスト用フック（関数差し替え）を考慮した実装になっていますが、実稼働環境でのレート制限・課金挙動の監視と詳細なリトライポリシー調整が推奨されます。
  - news_nlp / regime_detector のプロンプトや JSON パースは堅牢化されていますが、LLM 出力の多様性に対する追加のバリデーション・監査ログ強化を検討中。

0.1.0 - 2026-04-02
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開用の __version__ と __all__ を設定。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パーサを実装: コメント／export プレフィックス／シングル／ダブルクォートとエスケープ処理／インラインコメントの扱い等に対応。
  - 環境変数保護（protected keys）機構を導入し、OS の既存環境変数が誤って上書きされないようにした。
  - 設定取得ラッパー Settings を提供:
    - J-Quants / kabuステーション / Slack / データベースパス / 監視閾値 / システム環境判定（development/paper_trading/live）などのプロパティを実装。
    - 必須環境変数未設定時は ValueError を送出して明示的に失敗する設計。
    - env / log_level の値検証を追加（許容値外はエラー）。

- AI モジュール (kabusys.ai)
  - ニュース NLP (news_nlp)
    - raw_news / news_symbols を元に銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を算出。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）を提供（calc_news_window）。
    - バッチング（最大 20 銘柄／リクエスト）、記事数上限・文字数トリム、JSON Mode を使った堅牢なレスポンス検証を実装。
    - リトライポリシー（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンスのバリデーション機能を実装（JSON パース耐性、results 配列・code/score 検証、スコアの ±1.0 クリップ）。
    - DuckDB への書き込みは部分的置換（対象 code の DELETE → INSERT）を行い、部分失敗時に他コードの既存データを保護。

  - 市場レジーム判定 (regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を算出。
    - prices_daily / raw_news / market_regime を参照し、ルックアヘッドバイアスを防ぐクエリ条件を厳格に実装（target_date 未満の排他条件など）。
    - OpenAI 呼び出しは専用の実装で行い、API 障害時は macro_sentiment=0.0 にフォールバックして処理を継続するフェイルセーフ設計。
    - レジーム結果は冪等に market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試みて例外を伝播。

- 研究用モジュール (kabusys.research)
  - factor_research:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する calc_momentum を実装。データ不足時の挙動を明確化（None を返す）。
    - Volatility: 20 日 ATR（atr_20）や相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算する calc_volatility を実装。true_range の NULL 伝播制御など品質に配慮。
    - Value: raw_financials から最新の財務データを取得して PER / ROE を計算する calc_value を実装。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、SQL による一括取得）。
    - IC（Information Coefficient）計算 calc_ic（Spearman のランク相関、必要件数チェック含む）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - ファクター統計量要約 factor_summary（count/mean/std/min/max/median）。

  - research パッケージは外部依存をできる限り使わず、DuckDB 上の SQL と標準ライブラリのみで完結する設計。

- データプラットフォーム / ETL (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar）を操作するユーティリティ群を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供し、DB 登録がない場合は曜日ベースのフォールバックを行う設計。
    - calendar_update_job を実装し、J-Quants API から差分取得 → 冪等保存を行う（バックフィル・健全性チェックあり）。
  - pipeline & ETLResult:
    - ETL 実行結果を表す dataclass ETLResult を公開（取得数・保存数・品質問題・エラーの収集）。
    - pipeline モジュールは差分更新・保存（jquants_client 経由）・品質チェック（quality モジュール）という ETL の基本フローを実装方針として含む。
  - jquants_client との連携を想定した fetch/save の抽象化（外部クライアント呼び出し箇所を分離）。

- テスト容易性と運用配慮
  - OpenAI 呼び出し箇所にはテスト用に差し替え可能な仕組みを用意（unittest.mock.patch などで置換可能）。
  - DB 書き込みは冪等性を確保する設計（対象絞り込み DELETE → INSERT）で、部分失敗時のデータ保護を考慮。
  - ロギングを多用し、失敗時は WARN/INFO/EXCEPTION を出力するよう設計。

Security
- セキュリティ
  - API キーなどの必須環境変数が未設定の場合は明示的にエラーとなるため、秘密情報の取り扱いミスに気付きやすい設計。

Removed
- 該当なし（初回リリース）。

Changed
- 該当なし（初回リリース）。

Fixed
- 該当なし（初回リリース）。

Notes
- DuckDB バージョン差分や SQL バインドの挙動差異（例: executemany に空リストを渡せない等）をコード中で考慮しています。運用環境の DuckDB バージョンに応じた確認を推奨します。
- OpenAI モデルは gpt-4o-mini を想定しているため、将来モデル変更や SDK バージョン差分に対する互換性チェックが必要です。

Authors
- コードベースに含まれる実装に基づき changelog を作成しました。具体的な著者情報はリポジトリのコミット履歴を参照してください。