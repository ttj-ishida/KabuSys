CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" に準拠しています。  
フォーマットは簡略化していますが、主要な追加点・改善点・設計上の注意点を日本語でまとめています。

Unreleased
----------

- 改良: 環境変数パーサーのコメント/クォート処理をより堅牢に（エスケープ、インラインコメントの扱いの改善）
- 改良: OpenAI 呼び出し周りのリトライ・ログ出力の微調整（再試行間隔やログメッセージの明確化）
- 改良: DuckDB 実行時の executemany 空リスト回避ロジックの追加（互換性向上）
- ドキュメント: 各モジュールの設計方針・フェイルセーフ挙動に関する注記を追加

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース。主要な機能群を実装。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0"
    - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義

  - 環境変数・設定管理 (kabusys.config)
    - .env/.env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）
    - .env パーサー実装（export プレフィックス対応、クォート内エスケープ処理、インラインコメント扱い）
    - .env 読み込みを無効にするフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - Settings クラスを提供し、必須環境変数（J-Quants / kabu / Slack など）をプロパティ経由で取得
    - env / log_level の検証（許容値チェック）、DB パス設定の Path 変換

  - AI (kabusys.ai)
    - ニュースセンチメントスコアリング (news_nlp.score_news)
      - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出
      - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり記事数と文字数上限を設定
      - JSON Mode 応答の堅牢なパースとバリデーション、スコアの ±1.0 クリップ
      - リトライ戦略（429・ネットワーク断・タイムアウト・5xx）と指数バックオフ
      - 部分成功を考慮した ai_scores の冪等書き込み（該当 code の DELETE → INSERT）

    - 市場レジーム判定 (regime_detector.score_regime)
      - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成
      - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計（テスト時にモック可能）
      - DB の prices_daily / raw_news / market_regime を利用した日次判定・冪等書き込み
      - API エラー時のフェイルセーフ（macro_sentiment=0.0）やリトライ実装
      - レジームラベル: bull / neutral / bear（閾値・スケール設定あり）

  - データプラットフォーム (kabusys.data)
    - カレンダー管理 (calendar_management)
      - market_calendar を基にした営業日判定・前後営業日取得・期間内営業日列挙
      - DB 未取得日の曜日ベースフォールバック、SQ判定対応
      - JPX カレンダー差分取得バッチ（calendar_update_job）とバックフィル、健全性チェック

    - ETL パイプライン (pipeline, etl, jquants_client 統合想定)
      - ETLResult データクラスで ETL 実行結果を集約（品質チェック情報・エラーの集約）
      - 差分取得・バックフィル・品質チェック方針を実装方針として定義
      - ETL におけるテーブル最大日付取得・存在チェック等のユーティリティ

  - リサーチ (kabusys.research)
    - ファクター計算 (factor_research)
      - Momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算
      - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
      - Value: PER／ROE の取得（raw_financials と prices_daily の結合）
      - DuckDB SQL による効率的な集計と欠損扱い（データ不足時は None を返す）

    - 特徴量探索 (feature_exploration)
      - 将来リターン calc_forward_returns（任意ホライズン）
      - IC（Information Coefficient）計算（Spearman 相当のランク相関）
      - ランク変換ユーティリティ（同順位は平均ランク）
      - ファクター統計サマリー（count/mean/std/min/max/median）

Other changes / 設計上の注意
- ルックアヘッドバイアスの防止
  - 各モジュール（news/regime/factor/forward_returns 等）は内部で datetime.today()/date.today() を参照せず、呼び出し側から target_date を受け取る設計。
- フェイルセーフとロバストネス
  - OpenAI 呼び出し失敗時は例外を直ちに上位へ伝播させず、基本的にゼロスコアやスキップで継続する（サービス継続性重視）。
- テスト容易性
  - OpenAI 呼び出しを行う内部関数は patch により差し替え可能（ユニットテストでのモック容易化）。
- DuckDB 互換性への配慮
  - executemany の空リスト回避や date 型ハンドリングなど、DuckDB のバージョン差異を意識した実装。

Fixed
- （初版のため過去のバグ修正リストなし。実運用でのフィードバックに基づき修正予定）

Security
- API キーは引数または環境変数（OPENAI_API_KEY 等）での注入を要求。未設定時は明示的に ValueError を発生させ安全性を確保。

Deprecated
- なし

Notes / 今後の予定
- strategy, execution, monitoring パッケージの具体的な売買ロジック・実行・監視機能は今後のリリースで拡充予定
- テストカバレッジの強化、品質チェックルールの追加、パフォーマンス最適化（大規模 DB スキャン時）を予定
- OpenAI モデルの切替機構やローカル代替モデル対応、J-Quants / kabu API クライアントの詳細実装と認証フロー整備

ライセンスや配布に関する情報はリポジトリの README / pyproject.toml を参照してください。