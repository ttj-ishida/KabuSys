# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

### 予定 / 検討中
- CI / テスト用ユーティリティの追加
- ドキュメント（ユーザガイド・API リファレンス）の拡充
- 追加のログ・メトリクス出力（監視連携強化）

---

## [0.1.0] - 2026-04-04

初回公開リリース。日本株自動売買システムの基盤機能を実装しました。主要な機能群と実装上の設計方針を以下にまとめます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを公開。バージョンは 0.1.0。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト向け）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 既存 OS 環境変数を保護する protected オプション（.env の上書き制御）。
  - Settings クラスを実装し、J-Quants / kabu ステーション / LINE / DB / 監視 / システム周りの設定プロパティを提供（デフォルト値や型変換を含む）。
  - 必須環境変数未設定時の明示的なエラー報告 (_require)。

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp モジュール
    - score_news(conn, target_date, api_key=None)
      - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウ計算（calc_news_window）。
      - raw_news と news_symbols から銘柄ごとに記事を集約し、銘柄単位で OpenAI（gpt-4o-mini）にバッチ送信してセンチメントを取得。
      - バッチ処理（最大 20 銘柄/回）、1 銘柄あたり記事数／文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - レスポンスの厳格バリデーション（JSON 抽出、results 配列、各要素の code/score 検証）。
      - スコアは ±1.0 にクリップ。部分成功時を考慮して ai_scores テーブルへコード絞り込みで DELETE → INSERT（トランザクション）。
      - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
      - API 呼び出し箇所を置き換え可能にしてテスト容易性を確保（_call_openai_api のモック化を想定）。
  - regime_detector モジュール
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（_calc_ma200_ratio）とマクロニュース LLM センチメント（_score_macro）を重み合成（70% / 30%）してレジーム（bull/neutral/bear）を判定。
      - マクロキーワードで raw_news をフィルタしてタイトルを抽出し、OpenAI（gpt-4o-mini）で -1.0〜1.0 の JSON 応答を期待。
      - API エラーやパース失敗時は macro_sentiment=0.0（フェイルセーフ）。
      - 計算結果は market_regime テーブルに冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
      - OpenAI 呼び出しは retries/backoff を備え、HTTP 5xx とそれ以外を区別して処理。

- データ基盤 (kabusys.data)
  - pipeline / ETL
    - ETLResult データクラス（取得数・保存数・品質問題リスト・エラーリスト等）を定義し公開。
    - ETL 実行結果を辞書化する to_dict を実装（品質問題は簡易 dict に変換）。
    - ETL 設計方針: 差分取得、backfill（デフォルト 3 日）、品質チェックを統合する設計（jquants_client と quality モジュールの想定）。
  - calendar_management
    - JPX マーケットカレンダー管理と夜間バッチ更新（calendar_update_job）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。DB データがない場合は曜日ベースのフォールバック（週末除外）。
    - market_calendar が部分的にしか存在しない場合でも一貫性ある挙動を提供（DB 値優先、未登録日は曜日フォールバック）。
    - カレンダー先読み、バックフィル、最大探索日数や健全性チェック（サニティチェック）を実装。
    - jquants_client との連携を前提に fetch/save 関数を呼び出す設計。

- リサーチ / ファクター (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時の None 処理。
    - calc_volatility: 20 日 ATR、ATR 比（atr_pct）、20 日平均売買代金、出来高比率等を計算。true_range の NULL 伝播制御。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0 または NULL の場合は None）。
    - すべて DuckDB を用いた SQL / ウィンドウ関数ベースで実装（外部 API への依存なし）。
  - feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを LEAD により一括計算（ホライズン検証あり）。
    - calc_ic: スピアマン（ランク）相関による IC 計算。必要最低レコード数チェック（3 銘柄未満は None）。
    - rank, factor_summary: 同順位は平均ランクを与える実装、統計サマリー（count/mean/std/min/max/median）。
    - 標準ライブラリのみで数値処理を実装（pandas 等に依存しない）。

### 変更 (Changed)
- （初回リリースにつき過去バージョンからの変更履歴はありません）

### 修正 (Fixed)
- （初回リリースにつき過去バージョンからの修正履歴はありません）

### 設計上の注意 / フェイルセーフ
- ルックアヘッドバイアス防止のため、各モジュールは datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
- OpenAI API の失敗時はシステム全体が停止しないようフェイルセーフ（デフォルトスコア 0.0 やスキップ）を採用。
- DB 書き込みはトランザクションで行い、部分失敗時も既存データを過度に消さないよう配慮（部分 DELETE → INSERT）。
- テスト容易性: OpenAI 呼び出しや内部関数を差し替え可能（モック化）にしている箇所がある。

### 既知の制限 / TODO
- 一部の外部依存（jquants_client, quality モジュール、kabu ステーション連携等）はインターフェースを想定して実装しているため、実際の運用時は相互接続の実装・設定が必要。
- PBR・配当利回りなど一部ファクターは未実装（calc_value の注記）。
- news_nlp / regime_detector のプロンプト・キーワードは初期版。運用でチューニングが必要。

---

開発・運用上の詳細や API の使用例は各モジュールの docstring に記載しています。必要であれば、この CHANGELOG に追記するか、各機能ごとの詳細なリリースノートを作成します。