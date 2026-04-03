# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠し、
セマンティックバージョニングを採用します。

現在のバージョン: 0.1.0 (初回リリース) — 2026-04-03

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。
主にデータパイプライン、研究用ファクター計算、ニュース・LLM を用いた NLP/レジーム判定、
環境設定・カレンダー管理などの機能を含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加（__version__ = 0.1.0）。
  - public サブパッケージのエクスポート: data, strategy, execution, monitoring（将来の拡張用）。

- 環境設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - 読み込み順序: OS環境変数 > .env.local > .env。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパースに対応:
    - コメント行、export 前置、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理のサポート。
  - Settings クラスを提供:
    - J-Quants / kabu ステーション / LINE API / データベースパス / 監視設定 / システム設定 (env, log_level) 等のプロパティを定義。
    - デフォルト値や型変換（Path, float, bool）を扱う。
    - 必須値未設定時には _require が ValueError を送出。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
  - 主な特徴:
    - ジャストインタイムのタイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）。
    - 1 銘柄あたりのトークン肥大化対策（最大記事数・最大文字数でトリム）。
    - 最大 20 銘柄/チャンクでバッチ処理。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - JSON レスポンスの検証と ±1.0 クリッピング。
    - DuckDB への冪等書き込み（DELETE → INSERT）を採用し、部分失敗時に既存スコアを保護。
    - テストしやすさのため OpenAI API 呼び出しを差し替え可能（_call_openai_api を patch）。

- AI 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込み。
  - 主な特徴:
    - DuckDB からの過去データ取得は target_date 未満のみを使用し、ルックアヘッドバイアスを排除。
    - マクロ記事がない場合は LLM 呼び出しをスキップ（macro_sentiment=0.0）。
    - API エラー時はフェイルセーフで macro_sentiment=0.0 にフォールバック。
    - OpenAI 呼び出しは独立実装でモジュール結合を避け、テスト容易性を確保。

- 研究（Research）モジュール (src/kabusys/research/)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取り出し PER / ROE を計算（EPS が 0 または欠損時は None）。
    - DuckDB ベースの SQL 実装。外部 API へはアクセスしない（安全）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括計算（horizons の妥当性チェックあり）。
    - calc_ic: スピアマンランク相関（IC）計算（レコード不足時は None）。
    - rank: 同順位は平均ランクとして処理（float丸めで ties を扱う）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
  - research パッケージは一部ユーティリティを再エクスポート。

- データ処理 / ETL (src/kabusys/data/)
  - calendar_management:
    - JPX カレンダー管理、営業日判定・next/prev/get_trading_days・is_sq_day を提供。
    - market_calendar が未登録の領域は曜日ベースでフォールバック（土日非営業）。
    - calendar_update_job: J-Quants から差分取得して冪等保存、バックフィル、健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを追加（ETL 実行結果の集約、品質問題・エラーの格納、辞書化メソッド）。
    - ETL パイプライン設計: 差分取得・保存（jquants_client の save_* を利用）・品質チェックの呼び出し方針を定義。
    - DuckDB の互換性を考慮した実装（executemany に空リストを渡さないガード等）。
  - jquants_client / quality 等の具体的クライアント呼び出しは別モジュールとして想定（このリリース内で参照）。

- テスト支援・堅牢性
  - OpenAI 呼び出し抽象化により unittest.mock.patch による置換が容易（_call_openai_api を patch 可能）。
  - LLM API の失敗に対してはフォールバック動作（0.0 スコア、空辞書返却、処理継続）を設計に組み込み、実行時例外の伝播を最小化。

### 変更 (Changed)
- N/A（初回リリースのため履歴なし）

### 修正 (Fixed)
- N/A（初回リリースのため履歴なし）

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）。ただし以下の挙動は運用時に注意してください:
  - OpenAI API キー未設定時: score_news / score_regime は ValueError を送出します（api_key を引数経由で注入可能）。
  - .env 自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml が存在しない場合は自動ロードをスキップします）。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

### セキュリティ (Security)
- 外部 API（OpenAI / J-Quants）キーは環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）で管理することを想定。機密情報は .env に保存する場合も適切な運用を推奨。

### 注意事項 / 既知の制限 (Notes / Known limitations)
- DuckDB 固有の挙動に配慮しており、executemany に空リストを渡さない保護を実装しています。
- News NLP と Regime Detector は LLM の出力に依存するため、LLM モデルのレスポンス形式が変わるとパースロジックの調整が必要になる可能性があります。レスポンスパース失敗時はフェイルセーフでスコアを捨てます。
- price/financials テーブルのスキーマ・データ品質に依存します。ETL の品質チェック結果は ETLResult.quality_issues に蓄積され、呼び出し側での後続処理判断が必要です。
- Timezone は内部で UTC naive な datetime / date を扱う設計です（news ウィンドウは JST を基点に UTC に変換して DB と比較します）。運用時のタイムゾーン注意。

---

将来的なリリースでは以下を予定しています:
- strategy / execution / monitoring の具体的実装の追加（自動発注・ポートフォリオ管理・稼働監視）
- モデル選択・プロンプト改善・レスポンス検証の強化
- CI テスト用のモック実装とドキュメント拡充

もし CHANGELOG に追記してほしい観点（例えばモジュール別のより詳細な変更点や開発上のトラブルシュート情報）があれば教えてください。