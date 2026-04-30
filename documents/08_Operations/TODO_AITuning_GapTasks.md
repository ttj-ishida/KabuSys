# TODO: AIウィザード統合に向けたGap解消タスク

本ファイルは、KabuSysに「AI対話ウィザード（戦略チューニング機能）」および「Streamlit運用UI」を統合するために必要な、現在の設計・実装とのGapを解消するための具体的なアクションアイテム（TODOリスト）です。

## 1. 戦略パラメータの外部化（ハードコードの解消）
- [ ] 外部設定ファイルの策定（`config/strategy_config.json` または DBの `strategy_params` テーブルの設計）
- [ ] `src/kabusys/strategy/signal_generator.py` のリファクタリング
  - [ ] `_DEFAULT_WEIGHTS` などの固定値を設定ファイルから読み込むように変更する
  - [ ] ストップロス閾値（`-8%`）や Breadth Stop（`35%`）などのマジックナンバーをコードから除去する
- [ ] `src/kabusys/strategy/base.py` などの周辺モジュールでもハードコードされたパラメータがないか確認し改修する

## 2. バックテスト結果の構造化と永続化
- [ ] バックテスト履歴保存用のテーブルスキーマ設計（`backtest_runs`, `backtest_metrics`テーブルの定義）
- [ ] バックテスト実行スクリプトの改修
  - [ ] 結果をコンソールや一時CSV出力だけでなく、SQLite/DuckDBに `INSERT` するよう変更
- [ ] バックテスト結果からAI用の要約テキスト（Markdown等）を自動生成するモジュール（`src/kabusys/ai/metrics_summarizer.py` 等）の実装

## 3. 運用UI（Streamlitダッシュボード）基盤の構築
- [ ] 依存ライブラリ（`streamlit` 等）のインストールと `requirements.txt` の更新
- [ ] `src/kabusys/ui/app.py`（ダッシュボードのエントリーポイント）の作成
- [ ] UI上から `strategy_config.json` を編集・保存できる機能（チューニングパネル）の実装
- [ ] AI対話ウィザード（チャットUI）のコンポーネント化（`st.chat_message` を利用）
- [ ] OpenAI API を呼び出し、構造化されたバックテスト要約テキストをシステムプロンプトに注入する処理の実装

## 4. ドキュメントの整合性修正
- [ ] `documents/08_Operations/TODO_LineNotificationDesign.md` の運用フロー図にダッシュボードを追記
- [ ] 古い「バッチ処理のみ」を前提とした運用手順書（Runbook等）のアップデートと、UIベースの操作手順の記載
