# CHANGELOG

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に従っています。  
リリースはセマンティックバージョニングに準拠します。

## [0.1.0] - 2026-03-29
初回リリース — 基本的なデータ基盤、リサーチ、AI 評価、環境設定、ユーティリティ類を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ内モジュール群を __all__ で公開: data, research, ai, 等。

- 環境設定 / ロード機能 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - .env パーサはコメント行・export プレフィックス・シングル／ダブルクォート・バックスラッシュエスケープ等に対応。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境設定を取得する Settings クラスを実装（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベルなど）。
  - 必須変数未設定時に ValueError を投げるヘルパー _require を実装。
  - KABUSYS_ENV, LOG_LEVEL の妥当性検証を追加。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄ごとのニュースを LLM（gpt-4o-mini）へ送信し、銘柄別センチメント（ai_scores）を生成・書き込み。
    - バッチ処理（同時に最大 20 銘柄）・1銘柄当たり記事数・文字数の上限トリムなどトークン肥大化対策を実装。
    - JSON Mode を利用した厳密な JSON レスポンス期待と、JSON パースのフォールバック（本文から最外の {} を抽出）を実装。
    - レート制限 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - DuckDB への冪等書き込み（DELETE → INSERT、executemany の空リスト対策含む）。
    - テスト向けに _call_openai_api を差し替え可能（unittest.mock.patch を想定）。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を算出し、market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出のためのマクロキーワードリストを定義。
    - LLM 呼び出しでのリトライ・5xx/RateLimit/Timeout/接続エラーのハンドリングとフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - look-ahead バイアスを避ける設計（target_date 未満のデータのみを使用、date.today() を直接参照しない）。

- データ処理 / ETL (kabusys.data)
  - ETL パイプラインの公開インターフェース ETLResult（パラメータ・品質チェック結果・エラー情報を含むデータクラス）。
  - pipeline モジュール: 差分更新、バックフィル、品質チェックのためのユーティリティ（テーブル存在チェック、最終日取得など）。
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルを元に営業日判定・次/前営業日取得・期間内営業日取得・SQ日判定を提供。
    - DB 未取得時の曜日ベースフォールバック（週末を休場扱い）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存、バックフィルと健全性チェックを実装。
    - 最大探索日数やバックフィル日数などの安全パラメータを導入。

- リサーチ機能 (kabusys.research)
  - factor_research: ファクター計算（モメンタム、バリュー、ボラティリティ/流動性）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時の None ハンドリング）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials からの EPS/ROE と株価を組み合わせて PER/ROE を計算（EPS 0/欠損時は None）。
    - DuckDB SQL ベースでの実装。結果は (date, code) をキーとするレコードリストで返却。

  - feature_exploration: 将来リターン・IC・統計サマリー
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関を使った IC 計算（ties 平均ランク処理）。
    - rank: 値からランクへ変換（同順位は平均ランク、丸めで ties の検出漏れ対策）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

### 変更 (Changed)
- API 呼び出しの堅牢性向上
  - OpenAI 呼び出しに対するリトライ・バックオフ、レスポンスパースの堅牢化を導入し、API 停止時に処理を継続できるフェイルセーフ設計を採用。
  - DuckDB のバージョンや挙動（executemany の空リスト不可、リスト型バインドの互換性問題）を考慮した実装に調整。

- 設計方針の明確化
  - 全体として「ルックアヘッドバイアス防止」の原則に沿い、date.today() / datetime.today() を直接参照しない実装を徹底。
  - モジュール間の結合を避けるため、各モジュールで独立した _call_openai_api 実装を用意（テストで差し替え可能）。

### 修正 (Fixed)
- .env パーサの改善
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの判定改善を追加し、.env ファイルのパース不整合を低減。

- DB 書き込みの冪等性確保
  - ai_scores / market_regime への書き込みは DELETE → INSERT のパターンで実装し、部分失敗時に既存データを不必要に消さないように改善。

### 既知の制約 / 注意点 (Known limitations)
- OpenAI の JSON Mode に依存しているため、モデル応答のフォーマット変化に脆弱。パース時のフォールバックは導入済みだが、完全ではない可能性がある。
- DuckDB のバインディング / executemany の挙動はバージョン依存であるため、古い/新しい DuckDB での動作確認が必要。
- 現バージョンでは PBR・配当利回りなど一部バリューファクターは未実装。
- news_nlp / regime_detector は gpt-4o-mini を指定している。API キー未設定時は ValueError を投げる。
- calendar_update_job は jquants_client を利用するため、外部 API の利用制限や鍵管理に注意が必要。

### テスト向けフック
- OpenAI コールは各モジュール内の _call_openai_api を unittest.mock.patch などで差し替え可能。これにより外部 API を呼ばずにユニットテストが実行できます。

---

今後の予定例（メモ）
- PBR・配当利回りなどバリューファクターの追加実装。
- ai モデルのプラガブル化（モデル切り替え設定）。
- J-Quants クライアント周りのエラーハンドリング強化とリトライ戦略の統一化。
- ドキュメント・API リファレンスの整備。